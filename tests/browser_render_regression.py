"""Run with Playwright + Chromium; exercise real card DOM under HA state updates."""
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(f'http://127.0.0.1:{server.server_port}')
        source = (ROOT / 'thermostat-pro-timeline.js').read_text(encoding='utf-8')
        page.add_script_tag(content=source.replace('import.meta.url', '"http://localhost/card.js"'))
        page.evaluate('''async () => {
          const card = document.createElement('thermostat-timeline-card');
          card._loadStore = async () => {};
          card._hydrateUiNamesFromBackend = async () => {};
          card._debouncedSaveStore = () => {};
          card._startStoreWatchTimer = () => {};
          card.setConfig({entities:['climate.room'], auto_apply:false, storage_enabled:true});
          document.body.replaceChildren(card);
          card.hass = {states:{'climate.room':{state:'heat',attributes:{temperature:21,current_temperature:20}}},
            locale:{language:'en'}, language:'en', user:{is_admin:true}};
          await new Promise(resolve => setTimeout(resolve, 0));
          card._schedules['climate.room'] = {defaultTemp:18,blocks:[{id:'test',startMin:0,endMin:1440,temp:21}]};
          card._render();
          window.card = card;
          window.originalBlock = card.shadowRoot.querySelector('.block');
          if (!window.originalBlock) throw Error('No timeline block rendered');
          window.editCount = 0;
          card._openEditor = () => window.editCount++;
        }''')
        block = page.locator('thermostat-timeline-card .block').first
        block.click()
        page.evaluate('''() => {
          for (let i=0;i<20;i++) card.hass = {...card._hass, states:{...card._hass.states,'sensor.unrelated':{state:String(i)}}};
          if (originalBlock !== card.shadowRoot.querySelector('.block')) throw Error('Unrelated state update replaced block');
        }''')
        block.click(click_count=2)
        assert page.evaluate('window.editCount') == 1
        page.evaluate('''() => {
          const tap = () => originalBlock.dispatchEvent(new TouchEvent('touchend', {bubbles:true, cancelable:true}));
          tap();
          card.hass = {...card._hass, states:{...card._hass.states,'sensor.unrelated':{state:'next'}}};
          tap();
        }''')
        assert page.evaluate('window.editCount') == 2
        assert not errors, errors
        print('PASS: block DOM, double-click and double-tap survive unrelated HA updates')
        browser.close()
finally:
    server.shutdown()
