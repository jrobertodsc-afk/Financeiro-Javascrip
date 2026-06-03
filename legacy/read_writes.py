import json

log_path = r'C:\Users\Roberto\.gemini\antigravity\brain\4dba21dc-e8af-403d-8d0a-1c7e3d7533a0\.system_generated\logs\transcript.jsonl'
with open(log_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Get all write_to_file and replace_file_content actions to find what files were changed
for line in lines:
    try:
        obj = json.loads(line)
        if obj.get('type') == 'WRITE_FILE' or obj.get('type') == 'REPLACE_FILE_CONTENT' or obj.get('type') == 'MULTI_REPLACE_FILE_CONTENT':
            step = obj.get('step_index', '?')
            tool_calls = obj.get('tool_calls', [])
            for tc in tool_calls:
                args = tc.get('args', {})
                target = args.get('TargetFile', '')
                if target:
                    print(f'Step {step} [{obj["type"]}]: {target}')
    except:
        pass
