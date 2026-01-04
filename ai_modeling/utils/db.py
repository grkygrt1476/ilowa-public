# import csv
# import json
# import os

# def save_to_csv(list_of_dicts, path):
#     if not list_of_dicts:
#         return
    
#     # 디렉토리가 없으면 생성
#     os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    
#     keys = list(list_of_dicts[0].keys())
#     with open(path, "w", encoding="utf-8-sig", newline="") as f:
#         writer = csv.DictWriter(f, fieldnames=keys)
#         writer.writeheader()
#         for row in list_of_dicts:
#             writer.writerow(row)

# def save_sql_file(structured: dict, path: str):
#     def esc(s):
#         if s is None:
#             return ""
#         return str(s).replace("'", "''")
#     sql = f"""
# INSERT INTO jobs (
#     title, participants, hourly_wage, place, address, work_days,
#     start_time, end_time, client, description, embedding
# ) VALUES (
#     '{esc(structured.get('title',''))}',
#     {int(structured.get('participants', 0))},
#     {int(structured.get('hourly_wage', 0))},
#     '{esc(structured.get('place',''))}',
#     '{esc(structured.get('address',''))}',
#     '{esc(structured.get('work_days',''))}',
#     '{esc(structured.get('start_time','09:00:00'))}',
#     '{esc(structured.get('end_time','18:00:00'))}',
#     '{esc(structured.get('client',''))}',
#     '{esc(structured.get('description',''))}',
#     ''
# );
# """
#     with open(path, "w", encoding="utf-8") as f:
#         f.write(sql)
