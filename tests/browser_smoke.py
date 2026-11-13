"""Real browser smoke test. Creates only a fresh local demo account.

Run: python tests/browser_smoke.py [http://127.0.0.1:8000] [--screenshots]
Requires: pip install playwright && playwright install chromium
"""
import struct
import zlib
import secrets
import sys
import tempfile
import uuid
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = next((arg for arg in sys.argv[1:] if arg.startswith('http')), 'http://127.0.0.1:8000')
SHOTS = '--screenshots' in sys.argv
OUTPUT = ROOT / 'docs' / 'screenshots'


def screenshot(page, name):
    if SHOTS:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(OUTPUT / name), full_page=True, animations='disabled')


with sync_playwright() as playwright, tempfile.TemporaryDirectory() as temporary:
    browser = playwright.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE)
    expect(page.locator('#login')).to_be_visible()
    screenshot(page, '01-sign-in.png')
    # Register and sign in through the UI, rather than injecting a token.
    page.locator('#email').fill(f'demo-{uuid.uuid4().hex[:8]}@example.com')
    password = 'Demo' + secrets.token_hex(12)
    page.locator('#password').fill(password)
    page.locator('#register').click()
    expect(page.locator('#workspace')).to_be_visible()
    expect(page.locator('#emptyState')).to_be_visible()
    page.locator('#folder').fill('work/reports')
    page.locator('#tagInput').fill('работа')
    page.locator('#tagInput').press('Enter')
    payload = 'План проекта\nПодготовить документацию и проверить запуск.\n'.encode()
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
    colors = [(195, 238, 156), (38, 50, 42), (161, 168, 182)]
    pixels = b''.join(b'\x00' + b''.join(bytes(colors[min(x // 60, 2)]) for x in range(180)) for _ in range(120))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 180, 120, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')
    page.locator('#file').set_input_files([
        {'name': 'План проекта.txt', 'mimeType': 'text/plain', 'buffer': payload},
        {'name': 'Заметки по API.txt', 'mimeType': 'text/plain', 'buffer': b'API notes: upload, download, restore.'},
        {'name': 'Палитра.png', 'mimeType': 'image/png', 'buffer': png},
        {'name': 'Архив заметок.txt', 'mimeType': 'text/plain', 'buffer': b'An archived draft.'},
    ])
    page.locator('#uploadBtn').click()
    expect(page.locator('#fileCount')).to_have_text('4')
    row = page.locator('tr').filter(has=page.locator('.file-title', has_text='План проекта.txt'))
    with page.expect_download() as download_info:
        row.get_by_role('button', name='Скачать', exact=True).click()
    download = download_info.value
    download.save_as(str(Path(temporary) / 'download.txt'))
    assert (Path(temporary) / 'download.txt').read_bytes() == payload
    assert download.suggested_filename == 'План проекта.txt'
    # Preview works and object URLs are released when closing.
    page.get_by_role('button', name='Просмотр', exact=True).click()
    expect(page.locator('#previewDialog')).to_be_visible()
    expect(page.locator('#previewImage')).to_have_js_property('naturalWidth', 180)
    page.locator('#closePreview').click()
    expect(page.locator('#previewDialog')).not_to_be_visible()
    # Search + tag filtering.
    page.locator('#search').fill('Заметки по API')
    page.locator('#filterForm').get_by_role('button', name='Найти').click()
    expect(page.locator('#fileCount')).to_have_text('1')
    page.locator('#search').fill('')
    page.locator('#tagFilter').fill('работа')
    page.locator('#filterForm').get_by_role('button', name='Найти').click()
    expect(page.locator('#fileCount')).to_have_text('4')
    page.locator('#tagFilter').fill('')
    page.locator('#filterForm').get_by_role('button', name='Найти').click()
    archive = page.locator('tr').filter(has=page.locator('.file-title', has_text='Архив заметок.txt'))
    archive.get_by_role('button', name='Удалить', exact=True).click()
    expect(page.locator('#fileCount')).to_have_text('3')
    page.locator('#toast').wait_for(state='hidden')
    page.locator('#folder').fill('')
    page.locator('.chip button').click()
    screenshot(page, '02-library.png')
    page.locator('#stateFilter').select_option('deleted')
    expect(page.locator('#fileCount')).to_have_text('1')
    screenshot(page, '03-trash.png')
    page.get_by_role('button', name='Восстановить', exact=True).click()
    expect(page.locator('#emptyState')).to_be_visible()
    page.locator('#stateFilter').select_option('active')
    expect(page.locator('#fileCount')).to_have_text('4')
    # Malicious markup is rendered literally, never interpreted as HTML.
    page.locator('#tagInput').fill('<img src=x onerror=alert(1)>')
    page.locator('#tagInput').press('Enter')
    assert page.locator('#tagsChips img').count() == 0
    page.locator('.chip button').click()
    # Pagination is reachable beyond the default first page.
    page.locator('#file').set_input_files([
        {'name': f'page-{index}.txt', 'mimeType': 'text/plain', 'buffer': b'page'} for index in range(8)
    ])
    page.locator('#uploadBtn').click()
    expect(page.locator('#fileCount')).to_have_text('12')
    expect(page.locator('#filesTable tbody tr')).to_have_count(10)
    page.locator('#nextPage').click()
    expect(page.locator('#filesTable tbody tr')).to_have_count(2)
    page.locator('#prevPage').click()
    expect(page.locator('#filesTable tbody tr')).to_have_count(10)
    # Keep the mobile screenshot focused on the original sample files.
    page.locator('#search').fill('.png')
    page.locator('#filterForm').get_by_role('button', name='Найти').click()
    expect(page.locator('#fileCount')).to_have_text('1')
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.locator('#toast').wait_for(state='hidden')
    screenshot(page, '04-mobile.png')
    page.locator('#logout').click()
    expect(page.locator('#auth')).to_be_visible()
    assert page.locator('#filesTable tbody tr').count() == 0
    # Expired/invalid session returns to sign-in, not a broken workspace.
    page.evaluate("sessionStorage.setItem('fileStorageToken', 'invalid-session')")
    page.reload()
    expect(page.locator('#auth')).to_be_visible()
    assert not errors, errors
    browser.close()
    print('Browser checks passed: registration, upload, download bytes, preview, filters, trash, restore, safe tags, pagination, mobile, logout, invalid session.')
