import os, json

history_dir = os.path.expandvars(r'%APPDATA%\Code\User\History')
folders = {
    'MerchantDetail.vue': '-11816de2',
    'Rider.vue': '-e439a5b',
    'Merchant.vue': '39aec1ed',
    'Customer.vue': '4a597d03'
}

for name, folder in folders.items():
    entries_path = os.path.join(history_dir, folder, 'entries.json')
    if not os.path.exists(entries_path): continue
    with open(entries_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print('=== ' + name + ' ===')
    for entry in data['entries'][-10:]:
        entry_file = os.path.join(history_dir, folder, entry['id'])
        if not os.path.exists(entry_file): continue
        with open(entry_file, 'r', encoding='utf-8', errors='replace') as ef:
            content = ef.read()
        is_garbled = '??' in content or '' in content or 'ï¿' in content
        print('Entry ID: ' + entry['id'] + ', Timestamp: ' + str(entry.get('timestamp', 0)) + ', Garbled: ' + str(is_garbled))
