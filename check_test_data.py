import sqlite3

conn = sqlite3.connect('data/personas.db')
cursor = conn.cursor()

# Check what tables exist
cursor.execute('SELECT name FROM sqlite_master WHERE type=?', ('table',))
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])

# Check relationships for test personas
cursor.execute('SELECT * FROM relationships WHERE persona1_id LIKE ? OR persona2_id LIKE ?', ('%test', '%test'))
relationships = cursor.fetchall()
print(f'Test relationships: {len(relationships)}')
for rel in relationships[:3]:  # Show first 3
    print(f'  {rel[1]} -> {rel[2]}, interactions: {rel[6]}')

conn.close()