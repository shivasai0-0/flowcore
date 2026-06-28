import sqlite3
import json

def debug_session():
    conn = sqlite3.connect('flowcore.db')
    cur = conn.cursor()
    
    # 1. Get latest session
    cur.execute('SELECT id, business_id, customer_phone, fsm_state, current_node_id, workflow_version_id, carry_unit_json FROM sessions ORDER BY updated_at DESC LIMIT 1')
    row = cur.fetchone()
    if not row:
        print("No sessions found in the database.")
        conn.close()
        return
        
    session_id, business_id, phone, fsm_state, node_id, version_id, carry_json = row
    print("=== LATEST SESSION ===")
    print(f"Session ID: {session_id}")
    print(f"Business ID: {business_id}")
    print(f"Phone: {phone}")
    print(f"FSM State: {fsm_state}")
    print(f"Current Node: {node_id}")
    print(f"Workflow Version ID: {version_id}")
    
    # 2. Get active workflow info
    cur.execute('SELECT version_number, status, workflow_type, is_current FROM workflow_versions WHERE id = ?', (version_id,))
    wv = cur.fetchone()
    if wv:
        print(f"Workflow Version status: {wv[1]} (Version: {wv[0]}, Type: {wv[2]}, Current: {wv[3]})")
    else:
        print(f"Workflow Version {version_id} not found in workflow_versions!")
        
    # 3. Check compiled graph
    cur.execute('SELECT id FROM compiled_graphs WHERE workflow_version_id = ?', (version_id,))
    cg = cur.fetchone()
    print(f"Compiled graph exists: {cg is not None}")
    
    # 4. Get recent logs
    print("\n=== RECENT EXECUTION LOGS ===")
    cur.execute('SELECT node_id, module_name, fsm_state_before, fsm_state_after, executed_at FROM execution_logs WHERE session_id = ? ORDER BY executed_at DESC LIMIT 5', (session_id,))
    logs = cur.fetchall()
    for log in logs:
        print(f"Node: {log[0]} | Module: {log[1]} | {log[2]} -> {log[3]} | Time: {log[4]}")
        
    conn.close()

if __name__ == '__main__':
    debug_session()
