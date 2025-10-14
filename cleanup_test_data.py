import sqlite3

conn = sqlite3.connect('data/personas.db')
cursor = conn.cursor()

# Delete test relationships
test_personas = ['alice_test', 'bob_test', 'charlie_test']
for persona1 in test_personas:
    for persona2 in test_personas:
        if persona1 != persona2:
            cursor.execute('DELETE FROM relationships WHERE persona1_id = ? AND persona2_id = ?', (persona1, persona2))

# Delete emotional states
for persona_id in test_personas:
    cursor.execute('DELETE FROM emotional_states WHERE persona_id = ?', (persona_id,))

# Delete personas
for persona_id in test_personas:
    cursor.execute('DELETE FROM personas WHERE id = ?', (persona_id,))

conn.commit()
print('Cleaned test data')

# Verify cleanup
cursor.execute('SELECT COUNT(*) FROM relationships WHERE persona1_id LIKE ? OR persona2_id LIKE ?', ('%test', '%test'))
print(f'Remaining test relationships: {cursor.fetchone()[0]}')

conn.close()