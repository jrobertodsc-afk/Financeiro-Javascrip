import json

log_path = r'C:\Users\Roberto\.gemini\antigravity\brain\4dba21dc-e8af-403d-8d0a-1c7e3d7533a0\.system_generated\logs\transcript.jsonl'
with open(log_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Look at all commands (run_command) in the session to see git operations
for line in lines:
    try:
        obj = json.loads(line)
        if obj.get('type') in ('RUN_COMMAND', 'PLANNER_RESPONSE'):
            step = obj.get('step_index', '?')
            content = obj.get('content', '')
            tool_calls = obj.get('tool_calls', [])
            for tc in tool_calls:
                name = tc.get('name', '')
                args = tc.get('args', {})
                if name == 'run_command':
                    cmd = args.get('CommandLine', '')
                    if 'git' in cmd or 'historico' in cmd.lower() or 'descri' in cmd.lower():
                        print(f'Step {step}: {cmd[:200]}')
    except:
        pass
