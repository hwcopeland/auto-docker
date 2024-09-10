
import requests
import datetime
from collections import defaultdict
import plotly.express as px
from constants import DAG_ID, BASE_URL, SESSION_COOKIE, POOL_ALIAS

DAG_ID = 'test_dag'
DAG_RUN_IDS = [
    'manual__2023-06-14T12:27:47.923551+00:00',
    'manual__2023-06-14T12:27:49.523824+00:00',
    'manual__2023-06-14T12:27:50.758407+00:00',
    'manual__2023-06-14T12:27:52.001438+00:00'
]

pool_sizes = dict()

print('dag_id:', DAG_ID)
print('dag_run_ids:', ', '.join(DAG_RUN_IDS))

s = requests.Session()
s.cookies.set('session', SESSION_COOKIE)
s.headers['Content-type'] = 'application/json'

dates = []

for dag_run_id in DAG_RUN_IDS:
    print('run_id:', dag_run_id)

    r = s.get(f'{BASE_URL}/dags/{DAG_ID}/dagRuns/{dag_run_id}/taskInstances')
    d = r.json()

    """
    Parse tasks from JSON
    """
    for i, ti in enumerate(d['task_instances']):

        pool = ti['pool']
        if pool not in pool_sizes:
            pool_sizes[pool] = ti['pool_slots']
        else:
            assert pool_sizes[pool] == ti['pool_slots'], 'variable pool sizes during a DAG run is not supported'

        #print(ti['task_id'], ti.get('map_index'), ti['duration'])

        execution_date = datetime.datetime.fromisoformat(ti['start_date'])
        end_date       = datetime.datetime.fromisoformat(ti['end_date'])

        dates.append((execution_date, ti, 'start'))
        dates.append((end_date, ti, 'stop'))

dates.sort(key=lambda e: e[0])

pool_sizes = defaultdict(int)

"""
Create pool_sizes: pool_name -> pool_size
"""
tmp = defaultdict(int)
for d, ti, event in dates:

    pool, pool_slots = ti['pool'], ti['pool_slots']

    if event == 'start':
        tmp[pool] += pool_slots
    else:
        tmp[pool] -= pool_slots

    # update the pool size
    pool_sizes[pool] = max(pool_sizes[pool], tmp[pool])

print('pool_sizes:', pool_sizes)


"""
Create the Gantt chart data
"""
# slots[slot_id] = (next_available, tasks)
slots = {
    pool: [None] * pool_size 
    for pool, pool_size in pool_sizes.items()
}
df = []

for t, ti, event in dates: 
    pool = ti['pool']

    # slots for the pool where the current task is running
    ss = slots[pool]

    # ignore 'stop' events
    # TODO: remove those events entirely
    if event != 'start': continue

    # find first available pool
    for i, next_available in enumerate(ss):
        if next_available is None or next_available <= t:
            found = True
            break

    if not found: raise ValueError('incoherent planning :(')
    
    t_start = t
    t_end   = t + datetime.timedelta(seconds=ti['duration'])
    
    # set the next availability of the current slot
    ss[i] = t_end

    # --- Transformation for displaying as a Gantt chart ---
    map_index = None if ti['map_index'] == -1 else f'{ti["map_index"]}'

    pool = POOL_ALIAS.get(pool, pool)
    df.append({
        'task': ti['task_id'], 'start': t_start, 'end': t_end, 
        'resource': f'{pool}.{i}', 'map_index': map_index, 'dag_run_id': ti['dag_run_id']
    })
    # --- ---

t0 = dates[0][0]
delta = t0 - datetime.datetime.fromtimestamp(0, tz=t0.tzinfo)

for d in df:
    d['start'] = (d['start'] - delta)
    d['end']   = (d['end'] - delta)

df.sort(key=lambda e: e['resource'])

fig = px.timeline(df,
    x_start="start", x_end="end", y="resource", color="dag_run_id",
    labels={
        "resource": "Resources",
        "task": "Task",
        "map_index": "Batch ID",
        "dag_run_id": "DAG run",
    },
    width=28 * 30, height=12 * 30,
    color_discrete_sequence=px.colors.qualitative.G10
)
fig.update_xaxes(tickformat='%s', title='Time (s)')
fig.update_traces(textposition='inside')
fig.write_image("figures/gantt_multiexec.svg")
# fig.show()