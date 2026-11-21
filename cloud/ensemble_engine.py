"""Opt-in, unqualified until tested: semantic planning and real Saudi LoRA candidates."""
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import random
from threading import RLock
import time

from huggingface_hub import snapshot_download
from LABEQ_V16_Coaching_Engine import reply_v16
from candidate_selection import CONFIGURATIONS,decision_task
from cloud.semantic_teacher import SemanticTeacher,MODEL,MODEL_REVISION,WEIGHTS_SHA256
from grounded_review import REVIEW_MARKER,id_review_prompt
from writing_policy import read_policy

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(1024*1024):value.update(block)
    return value.hexdigest()


class EnsembleEngine:
    reply_source='qwen_lora_generated'
    review_prompt_builder=staticmethod(id_review_prompt)
    compute_backend='torch-cpu-ensemble'

    @property
    def generation_trace(self):return self.writer.generation_trace

    def __init__(self,writer,teacher=None):
        self.writer=writer;self.teacher=teacher or SemanticTeacher();self.lock=RLock()
        directory=os.getenv('LABEQ_V2_ADAPTER_DIR')
        if directory:
            self.v2_directory=Path(directory);self.v2_revision=os.getenv('LABEQ_V2_ADAPTER_REVISION','local-private-QA')
        else:
            repo=os.environ['LABEQ_V2_ADAPTER_REPO'];self.v2_revision=os.environ['LABEQ_V2_ADAPTER_REVISION']
            subfolder=os.getenv('LABEQ_V2_ADAPTER_SUBFOLDER','')
            prefix=subfolder+'/' if subfolder else ''
            self.v2_directory=Path(snapshot_download(repo,revision=self.v2_revision,
                allow_patterns=[prefix+'adapter_config.json',prefix+'adapter_model.safetensors']))/subfolder
        config=json.loads((self.v2_directory/'adapter_config.json').read_text())
        if config.get('base_model_name_or_path') not in {'Qwen/Qwen3.5-4B','unsloth/Qwen3.5-4B'}:raise ValueError('Incompatible second adapter')
        self.adapter_sha256=writer.adapter_sha256
        if os.getenv('LABEQ_PILOT_SHA256') and self.adapter_sha256!=os.environ['LABEQ_PILOT_SHA256']:raise ValueError('Primary adapter checksum mismatch')
        self.adapter_labels={'pilot':writer.adapter_label,'v2':os.getenv('LABEQ_V2_ADAPTER_LABEL','Saudi LoRA v2')}
        self.candidate_adapter_shas={'pilot':writer.adapter_sha256,'v2':digest(self.v2_directory/'adapter_model.safetensors')}
        if len(set(self.candidate_adapter_shas.values()))!=2:raise ValueError('Distinct candidate adapter weights required')
        expected=os.getenv('LABEQ_V2_SHA256')
        if expected and self.candidate_adapter_shas['v2']!=expected:raise ValueError('Second adapter checksum mismatch')
        self.policies={};self.policy_shas={}
        for key,path in [('clean',ROOT/'training/generalization_v3/policy.json'),('fewshot',ROOT/'training/qwen36_cpu/writer_fewshot.json')]:
            self.policies[key]=read_policy(path);self.policy_shas[key]=digest(path)
        self.model=None;self.faisal_ready=False;self.rng=random.Random(20261122)
        self.base_revision=writer.base_revision;self.adapter_revision=writer.adapter_revision
        self.faisal_revision=writer.faisal_revision
        self.environment_versions=dict(writer.environment_versions)
        self.environment_versions['llama-cpp-python']=version('llama-cpp-python')
        self.generator=f"Qwen3.5-4B + {self.adapter_labels['pilot']}/{self.adapter_labels['v2']} candidates; Qwen3.6 semantic planning, selection and review (CPU)"
        self.repetition_penalty=1.0;self.writer.repetition_penalty=1.0
        self.writer.generation_time_limit=22
        self.last_writer_provenance={};self.attempt_trace=[]

    def load(self):
        with self.lock:
            if self.model is not None:return self
            self.writer.load()
            self.writer.model.load_adapter(str(self.v2_directory),adapter_name='saudi_v2',is_trainable=False,torch_device='cpu')
            self.writer.model.set_adapter('saudi');self.writer.model.eval()
            self.teacher.load();self.model=self.writer.model;self.faisal_ready=self.writer.faisal_ready
            return self

    def deployment_metadata(self):
        return {'candidate_adapter_shas':self.candidate_adapter_shas,'candidate_configurations':CONFIGURATIONS,
            'candidate_policy_sha256':self.policy_shas,'v2_adapter_revision':self.v2_revision,
            'planning_model':MODEL,'planning_model_revision':MODEL_REVISION,'planning_weights_sha256':WEIGHTS_SHA256,
            'planning_weights_verified':self.teacher.verified,'candidate_selection_model':MODEL,'review_model':MODEL}

    def predict_style(self,message,relation,goal):
        result=self.writer.predict_style(message,relation,goal)
        self.last_router_result={'style':result[0],'router_source':result[1]}
        self.writer.deadline=self.deadline
        return result

    def _one_generation(self,messages,retry=False,use_adapter=True,max_tokens=256):
        if not use_adapter:
            text=messages[-1]['content']
            if text.startswith(REVIEW_MARKER):return self.teacher.review(json.loads(text[len(REVIEW_MARKER):]),self.deadline)
            amended=[dict(item) for item in messages]
            amended[-1]['content']+='\nتحليل آلي استرشادي، والنص الأصلي هو المرجع:\n'+json.dumps(self.automatic_plan,ensure_ascii=False)
            return self.teacher.generate(amended,max_tokens,self.deadline,'coaching')
        candidates={};failures=[]
        for configuration in CONFIGURATIONS:
            adapter,policy=configuration.split('_',1)
            if time.monotonic()>=self.deadline-6:break
            self.writer.active_writer_adapter='saudi' if adapter=='pilot' else 'saudi_v2'
            self.writer.deadline=self.deadline-6
            system,examples=self.policies[policy]
            text=messages[-1]['content']+'\nتحليل آلي استرشادي للطلبات، وليس مصدرا للحقائق. النص الأصلي هو المرجع إذا تعارض معه:\n'+json.dumps(self.automatic_plan,ensure_ascii=False)
            prompt=[{'role':'system','content':system}]+[dict(x) for x in examples]+[{'role':'user','content':text}]
            try:
                reply=self.writer._one_generation(prompt,retry=retry,use_adapter=True,max_tokens=max_tokens)
                candidates[configuration]={'reply':reply,'generation':dict(self.writer.last_generation),
                    'adapter':adapter,'adapter_sha256':self.candidate_adapter_shas[adapter],
                    'adapter_revision':self.adapter_revision if adapter=='pilot' else self.v2_revision,
                    'policy_sha256':self.policy_shas[policy]}
            except Exception as exc:failures.append({'configuration':configuration,'error_type':type(exc).__name__})
        if not candidates:raise RuntimeError('No complete model candidate available')
        task,mapping=decision_task(self.current_case,self.automatic_plan,{key:value['reply'] for key,value in candidates.items()},self.rng)
        choice=self.teacher.select(task,self.deadline)
        attempt={'retry':retry,'candidates':candidates,'failures':failures,'selection_task':task,
            'anonymous_key':mapping,'selection_label':choice,'selected_configuration':mapping.get(choice)}
        self.attempt_trace.append(attempt)
        if choice not in mapping:raise RuntimeError('Model rejected all generated candidates')
        name=mapping[choice];selected=candidates[name]
        self.last_writer_provenance={'configuration':name,'adapter':selected['adapter'],
            'adapter_sha256':selected['adapter_sha256'],'adapter_revision':selected['adapter_revision'],
            'policy_sha256':selected['policy_sha256'],'selection_model':MODEL,'selection_label':choice,
            'generator':f"Qwen3.5-4B + {self.adapter_labels[selected['adapter']]} (bfloat16 CPU; Qwen3.6 planning/selection/review)"}
        return selected['reply']

    def reply(self,message,relation='صديق',goal='أبي رد مناسب وواضح',style='تلقائي',
              speaker_gender='غير محدد',recipient_gender='غير محدد',history=None,generation_mode='موجّه'):
        with self.lock:
            self.load();self.deadline=time.monotonic()+135;self.writer.deadline=self.deadline
            self.teacher.trace=[];self.writer.generation_trace=[];self.attempt_trace=[];self.last_writer_provenance={}
            self.last_router_result=None
            self.current_case={'message':message,'relation':relation,'goal':goal}
            if speaker_gender!='غير محدد':self.current_case['speaker_gender']=speaker_gender
            if recipient_gender!='غير محدد':self.current_case['recipient_gender']=recipient_gender
            try:
                self.automatic_plan=self.teacher.plan(self.current_case,self.deadline)
                result=reply_v16(self,message,relation,goal,style,speaker_gender,recipient_gender,history,generation_mode)
            except Exception as exc:
                if os.getenv('LABEQ_RETURN_GENERATION_TRACE')=='1':
                    return {'status':'generation_failed','error_type':type(exc).__name__,
                        'teacher_trace':self.teacher.trace,'candidate_attempts':self.attempt_trace,'actual_router_result':self.last_router_result}
                raise
            result.update(automatic_meaning_plan=self.automatic_plan,meaning_plan_status='model_generated_unverified',
                planning_model=MODEL,candidate_selection_model=MODEL,review_model=MODEL)
            if os.getenv('LABEQ_RETURN_GENERATION_TRACE')=='1':
                result['teacher_trace']=self.teacher.trace;result['candidate_attempts']=self.attempt_trace
            return result

    configured_reply=reply
