"""Source coverage/provenance contracts; these do not grade model semantics."""
import json
import pytest
from grounded_review import attach_source_quotes,source_units
from semantic_review import parse_review

MESSAGE='أقدر أطبخ، بس ما أقدر أوصل. أبي هي ترتب التوصيل.'
GOAL='أرفض جزء وأقبل جزء'


def verdict(sources):
    return {'checks':{key:{'status':'met','reason':''} for key in sources},'unsupported':[],'language_issues':[]}


def test_quote_provenance_and_complete_source_coverage_are_server_owned():
    sources=source_units(MESSAGE,GOAL)
    data=verdict(sources)
    text=attach_source_quotes(json.dumps(data),sources)
    parsed=parse_review(text,MESSAGE,GOAL,'أقدر أطبخ بس التوصيل ترتبينه أنت.')
    assert parsed['valid'] and len(parsed['checks'])==len(sources)
    assert all(x['source_quote'] in MESSAGE+'\n'+GOAL for x in parsed['checks'])
    del data['checks'][next(iter(sources))]
    with pytest.raises(ValueError,match='Every source ID'):
        attach_source_quotes(json.dumps(data),sources)


def test_language_issue_must_quote_actual_candidate_text():
    sources=source_units(MESSAGE,GOAL);data=verdict(sources)
    data['language_issues']=[{'quote':'بدالي','reason':'Pronoun reverses whose report is being written.'}]
    raw=attach_source_quotes(json.dumps(data),sources)
    assert not parse_review(raw,MESSAGE,GOAL,'أقدر أطبخ بس ما أقدر أوصل.')["valid"]
    result=parse_review(raw,MESSAGE,GOAL,'ما أكتب تقريرك بدالي.')
    assert result['valid'] and result['issues']


def test_many_source_units_do_not_discard_the_end_of_the_request():
    message=''.join(f'طلب رقم {i}.' for i in range(20))
    sources=source_units(message,GOAL)
    assert message in sources.values() and len(sources)<=12


@pytest.mark.parametrize('message,goal',[('لا. أبي أوضح إن هالطلب ما يناسبني.','أوضح حدودي'),(MESSAGE,'رد')])
def test_short_units_and_goals_still_allow_a_grounded_review(message,goal):
    sources=source_units(message,goal)
    text=attach_source_quotes(json.dumps(verdict(sources)),sources)
    assert parse_review(text,message,goal,'هذي صياغة للاختبار وليست قياس جودة')['valid']
