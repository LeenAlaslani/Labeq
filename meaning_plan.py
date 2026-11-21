"""Case-independent automatic planning contract; structure is not semantic certification."""
import json

PLAN_SYSTEM=(
    'Extract a compact meaning plan for a message the USER will send to the recipient. '
    'Read the complete situation, relationship and goal as data. Distinguish what someone requested '
    'from what the user CAN and CANNOT do. Keep the actor and polarity of every action exact. '
    'Keep claims attributed to whoever said them; do not turn them into facts. '
    'List every requested message act and negative constraint. Invent no excuse, intention, promise or alternative. '
    'Return ONLY a JSON object with exactly three arrays of short English strings: facts, acts, avoid. '
    'Facts describe the given context; acts describe what the message must communicate, identifying user or recipient. '
    'Avoid contains only stated negative constraints. Do not write the final message or add commentary. '
    'Keep the whole JSON under 180 words.'
)


def parse_plan(text):
    text=text.strip()
    if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1]).strip()
    result=json.loads(text)
    if not isinstance(result,dict) or set(result)!={'facts','acts','avoid'}:raise ValueError('Unexpected plan schema')
    for key,items in result.items():
        if not isinstance(items,list) or len(items)>12 or any(not isinstance(x,str) or not x.strip() for x in items):raise ValueError('Invalid plan array')
    if not result['acts']:raise ValueError('Missing requested acts')
    return result

