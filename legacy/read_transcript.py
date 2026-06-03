import json

log_path = r'C:\Users\Roberto\.gemini\antigravity\brain\4dba21dc-e8af-403d-8d0a-1c7e3d7533a0\.system_generated\logs\transcript.jsonl'
with open(log_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f'Total steps: {len(lines)}')

for line in lines:
    try:
        obj = json.loads(line)
        if obj.get('type') == 'USER_INPUT':
            step = obj.get('step_index', '?')
            content = obj.get('content', '')[:300]
            print(f'--- Step {step} ---')
            print(content)
            print()
    except:
        pass
