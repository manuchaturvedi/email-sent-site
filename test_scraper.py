#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')

from sendmail.app import scrape_and_save_jobs
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

print('=' * 80)
print('MANUAL SCRAPE TEST')
print('=' * 80)

try:
    print('\n🔍 Starting LinkedIn scrape...')
    print('Search: "Devops hiring OR Engineer hiring"')
    print('Time Period: past-week')
    print('Scrolls: 3\n')
    
    result = scrape_and_save_jobs(
        search_role='Devops hiring OR Engineer hiring',
        search_time='past-week',
        user_email='test@justmailit.in',
        scrolls=3
    )
    
    print('\n' + '=' * 80)
    print('✅ SCRAPE COMPLETED SUCCESSFULLY!')
    print('=' * 80)
    print(f'Result: {result}')
    
except Exception as e:
    print('\n' + '=' * 80)
    print('❌ SCRAPE FAILED!')
    print('=' * 80)
    print(f'Error: {str(e)}')
    import traceback
    traceback.print_exc()
