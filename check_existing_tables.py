#!/usr/bin/env python3
"""
Check existing database tables to see if interaction_history already existed
"""
import sqlite3

def check_existing_tables():
    conn = sqlite3.connect('data/personas.db')
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print('All tables in database:')
    for table in tables:
        print(f'  {table[0]}')
    
    # Check if any existing tables might track interactions
    print('\nChecking for interaction-related tables:')
    for table in tables:
        table_name = table[0]
        if 'interaction' in table_name.lower() or 'history' in table_name.lower() or 'conversation' in table_name.lower():
            print(f'\nTable: {table_name}')
            cursor.execute(f'PRAGMA table_info({table_name})')
            columns = cursor.fetchall()
            print('  Columns:')
            for col in columns:
                print(f'    {col[1]} ({col[2]})')
                
            # Show sample data if any
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                count = cursor.fetchone()[0]
                print(f'  Row count: {count}')
                if count > 0 and count <= 5:
                    cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
                    rows = cursor.fetchall()
                    print('  Sample data:')
                    for row in rows:
                        print(f'    {row}')
            except Exception as e:
                print(f'  Error checking data: {e}')
    
    conn.close()

if __name__ == '__main__':
    check_existing_tables()