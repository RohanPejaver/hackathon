/* Station display + inspector renderer. One snapshot in, DOM out. No library, no build step.
   The worker never mutates state: every tap is POST /action, which becomes an event (22). */
(() => {
  const page = document.body.dataset.page;
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const icon = (n) => `<svg class="ph"><use href="/static/vendor/icons/phosphor-sprite.svg#ph-${n}"/></svg>`;
  const KIND_ICON = { GLOVES: 'hand', TOOL: 'knife', SURFACE: 'square', CONTAINER: 'jar', FOOD: 'bread' };
  const ACTION_ICON = { NEW_GLOVES: 'hand', SWAP_TOOL: 'arrows-clockwise', SWAP_SURFACE: 'square', USE_SEALED_BACKUP: 'warning', SEQUENCE_TICKETS: 'list-checks' };
  const ASSERT_LABEL = { NEW_GLOVES: 'Already changed', SWAP_TOOL: 'Already swapped', SWAP_SURFACE: 'Already swapped', USE_SEALED_BACKUP: 'Using sealed backup' };
  const GRADE_ABBR = { OBSERVED: 'obs', INFERRED: 'inf', ASSERTED: 'asr', PESSIMISTIC: 'pes' };
  const MODE_TEXT = { FULL: 'FULL', PROTOCOL_ONLY: 'PROTOCOL ONLY — VISION UNAVAILABLE', REPLAY: 'REPLAY', CALIBRATION: 'CALIBRATION' };
  const KIND_ORDER = { GLOVES: 0, TOOL: 1, SURFACE: 2, CONTAINER: 3, FOOD: 4 };
  const OPEN = new Set(['RAISED', 'ACKNOWLEDGED', 'ESCALATED']);
  const LIVE_TICKET = new Set(['RECEIVED', 'BLOCKED', 'BOUND', 'IN_PREP', 'COMPLETE', 'HELD']);

  let snap = null;

  const fmtT = (t) => {
    if (t == null) return '—';
    if (snap && snap.time.kind === 'WALL') return new Date(t).toTimeString().slice(0, 8);
    const s = Math.floor(t / 1000);
    return `+${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}.${Math.floor((t % 1000) / 100)}`;
  };
  const ago = (t) => {
    if (t == null) return 'never';
    const d = Math.max(0, snap.time.t - t);
    return d < 1000 ? 'now' : d < 60000 ? `${Math.floor(d / 1000)}s` : `${Math.floor(d / 60000)}m`;
  };

  async function act(body) {
    const r = await fetch('/action', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ worker_slot: 0, ...body }) });
    if (!r.ok) console.warn('action refused', await r.text());
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-act]');
    if (!b) return;
    act(JSON.parse(b.dataset.act));
  });

  function renderTop(s) {
    $('station').textContent = s.station_id;
    const down = s.health.reasoning === 'DOWN';
    $('banner').dataset.mode = down ? 'DOWN' : s.mode;
    $('banner-text').textContent = down ? 'REASONING DOWN — PROTOCOL ONLY' : MODE_TEXT[s.mode];
    $('banner-why').textContent = s.health.message || '';
    $('h-vision').textContent = s.health.vision;
    $('h-reasoning').textContent = s.health.reasoning;
    $('h-late').textContent = `${Math.round(s.health.late_rate * 100)}%`;
    $('h-rejected').textContent = s.health.rejected_events;
    $('clock').textContent = fmtT(s.time.t);
    if ($('h-cfg')) { $('h-cfg').textContent = `v${s.config_version}`; $('h-kv').textContent = `v${s.knowledge_version}`; }
  }

  function restrLine(r) {
    const txt = r.resolution === 'RESOLVED' ? r.allergen_ids.join(', ') : r.resolution;
    return `<div class="restr" data-resolution="${r.resolution}">${esc(txt)} <span class="raw">“${esc(r.raw_text)}”</span></div>`;
  }
  function ticketButtons(t) {
    if (page !== 'worker') return '';
    const b = (label, act, kind = 'quiet') => `<button class="btn small" data-kind="${kind}" data-act='${esc(JSON.stringify({ ...act, ticket_id: t.ticket_id }))}'>${label}</button>`;
    if (t.lifecycle === 'RECEIVED') return b('Bind', { kind: 'BIND_TICKET' }, 'primary');
    if (t.lifecycle === 'BOUND') return b('Start prep', { kind: 'PREP_STARTED' });
    if (t.lifecycle === 'IN_PREP') return b('Item complete', { kind: 'ITEM_COMPLETE' });
    if (t.lifecycle === 'BLOCKED') return `<span class="micro">restriction unresolved — ask front of house</span>`;
    return '';
  }
  function renderTickets(s) {
    const live = s.tickets.filter((t) => LIVE_TICKET.has(t.lifecycle));
    $('tickets-count').textContent = live.length;
    const cards = live.map((t) => `
      <div class="ticket" data-lifecycle="${t.lifecycle}" data-restricted="${t.restrictions.some((r) => r.allergen_ids.length || r.resolution !== 'RESOLVED') ? 1 : 0}">
        <div class="row"><span class="id">#${esc(t.ticket_id)}</span><span class="life micro">${t.lifecycle.replace('_', ' ')}</span></div>
        <div class="items">${t.items.map((i) => esc(i.display_name)).join(' · ')}</div>
        ${t.restrictions.map(restrLine).join('')}
        <div class="row" style="margin-top:6px">${ticketButtons(t)}</div>
      </div>`);
    const form = page === 'worker' ? `
      <div class="ticket" data-lifecycle="RECEIVED">
        <div class="micro" style="margin-bottom:6px">New ticket</div>
        <div class="row"><input id="nt-id" class="mono" placeholder="id" size="4"> <select id="nt-item">${s.menu.map((m) => `<option value="${esc(m.item_id)}">${esc(m.display_name)}</option>`).join('')}</select></div>
        <div class="row" style="margin-top:6px"><input id="nt-restr" placeholder="restriction note (optional)" style="flex:1"> <button class="btn small" id="nt-go">Enter</button></div>
      </div>` : '';
    $('tickets').innerHTML = (cards.join('') || '<div class="empty">No tickets</div>') + form;
    const go = $('nt-go');
    if (go) go.onclick = () => {
      const id = $('nt-id').value.trim(); if (!id) return;
      const raw = $('nt-restr').value.trim();
      act({ kind: 'NEW_TICKET', ticket_id: id, items: [$('nt-item').value], restrictions: raw ? [{ raw_text: raw }] : [] });
      $('nt-id').value = ''; $('nt-restr').value = '';
    };
  }

  function eventLine(e) {
    return `<div class="log-line" data-mutates="${e.mutates_state ? 1 : 0}" data-source="${e.source}" data-late="${e.late ? 1 : 0}">
      <span class="t">${fmtT(e.t_occurred)}</span><span class="type">${esc(e.type)}</span><span class="parts">${esc(e.summary)}</span><span class="grade">${esc(e.grade || '')}</span></div>`;
  }
  function renderLog(s, upto) {
    const evs = upto == null ? s.recent_events : s.recent_events.filter((e) => e.seq <= upto);
    $('log-count').textContent = `seq ${s.seq}`;
    const el = $('log');
    el.innerHTML = evs.map(eventLine).join('') || '<div class="empty">No observations yet</div>';
    el.scrollTop = el.scrollHeight;
  }

  function tile(c) {
    const tainted = c.taints.length > 0;
    const chips = c.taints.map((t) => `<span class="taint" data-grade="${t.grade}" data-strength="${t.strength}">${esc(t.allergen_id)}<span class="g">${GRADE_ABBR[t.grade]}${t.hops ? ` h${t.hops}` : ''}${t.strength === 'POSSIBLE' ? ' ?' : ''}</span></span>`).join('');
    const src = c.source_allergens.length ? `<span class="micro">holds ${esc(c.source_allergens.join(', '))}</span>` : '';
    const shared = tainted && c.shared ? `<div class="shared">${icon('warning')} Shared container — ${esc([...new Set(c.taints.map((t) => t.allergen_id))].join(', '))} — affects all future tickets</div>` : '';
    const wiped = c.last_wiped_at != null ? `<span class="micro">wiped ${ago(c.last_wiped_at)} · not a reset</span>` : '';
    return `<div class="tile" data-epi="${c.epistemic}" data-tainted="${tainted ? 1 : 0}" data-kind="${c.kind}">
      <div class="tile-head">${icon(KIND_ICON[c.kind])}<span class="id">${esc(c.carrier_id)}</span><span class="kind micro">${c.kind}</span></div>
      <div class="tile-taints">${chips || src}</div>${shared}
      <div class="tile-foot"><span class="epi">${c.epistemic}</span>${wiped}<span class="ago">${c.epistemic === 'UNKNOWN' ? 'not observed' : `seen ${ago(c.last_observed_at)}`}</span></div>
    </div>`;
  }
  function renderGrid(s) {
    const cs = [...s.carriers].sort((a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind] || a.carrier_id.localeCompare(b.carrier_id));
    $('carriers-count').textContent = cs.length;
    $('grid').innerHTML = cs.map(tile).join('');
  }

  function traceLines(d) {
    return d.map((st) => st.kind === 'ABSENCE'
      ? `<div class="trace-line absent"><span class="t">—</span><span>-- ${esc(st.narrative)} --</span></div>`
      : `<div class="trace-line ${st.kind.toLowerCase()}"><span class="t">${fmtT(st.t_occurred)}</span><span class="type">${esc(st.type || '')}</span><span class="delta">${esc(st.narrative)}${st.state_delta ? ` · ${esc(st.state_delta)}` : ''}</span><span class="grade">${esc(st.grade || '')}</span></div>`).join('');
  }
  function renderRisk(s) {
    const open = s.alerts.filter((a) => OPEN.has(a.state)).sort((a, b) => b.tier - a.tier || a.raised_at - b.raised_at);
    $('alerts-count').textContent = open.length;
    const all = page === 'inspector' ? [...s.alerts].sort((a, b) => b.raised_at - a.raised_at) : open;
    $('risk').innerHTML = all.map((a) => `
      <div class="alert" data-tier="${a.tier}">
        <div class="row"><span class="micro">Tier ${a.tier} · #${esc(a.ticket_id)} · ${esc(a.allergen_id)}</span><span class="state micro">${esc(a.state)}</span></div>
        <div class="head">${esc(a.headline)}</div>
        <div class="trace">${traceLines(a.derivation)}</div>
      </div>`).join('') || '<div class="empty">Quiet</div>';
  }

  function surfaceFor(s) {
    const open = s.alerts.filter((a) => OPEN.has(a.state) && !(a.dismissed_until != null && a.dismissed_until > s.time.t));
    open.sort((a, b) => b.tier - a.tier || a.raised_at - b.raised_at);
    if (open.length) return { alert: open[0] };
    const held = s.tickets.find((t) => t.lifecycle === 'HELD');
    return held ? { held } : {};
  }
  function renderSurface(s) {
    const el = $('surface');
    const { alert: a, held } = surfaceFor(s);
    if (!a && !held) {
      el.dataset.tier = 'none';
      el.innerHTML = `<div class="label micro">${s.condition.multi_restriction ? 'Two active restrictions — sequence them' : 'Station quiet'}</div><h1 class="headline">Nothing to do</h1>`;
      return;
    }
    if (held) {
      el.dataset.tier = '2';
      el.innerHTML = `<div class="label micro">Tier 2 · Hold · Ticket ${esc(held.ticket_id)} · awaiting release</div>
        <h1 class="headline">HELD — TICKET ${esc(held.ticket_id)}</h1>
        <div class="actions"><button class="btn" data-kind="primary" data-act='${esc(JSON.stringify({ kind: 'RESOLVE_HOLD', ticket_id: held.ticket_id }))}'>${icon('check')} Release ticket</button>
        <button class="btn" data-kind="hold" data-act='${esc(JSON.stringify({ kind: 'REMAKE', ticket_id: held.ticket_id }))}'>${icon('arrow-counter-clockwise')} Remake</button></div>
        <div class="disclaimer">Only a person releases a hold. The system never does.</div>`;
      return;
    }
    el.dataset.tier = String(a.tier);
    const assertAll = (claim, label, kind) => {
      const carriers = a.required_actions.filter((r) => r.carrier_id && !r.done).map((r) => r.carrier_id);
      return carriers.length ? `<button class="btn" data-kind="${kind}" data-act='${esc(JSON.stringify({ kind: claim, alert_id: a.alert_id, carrier_ids: carriers }))}'>${icon('check')} ${label}</button>` : '';
    };
    const dismiss = `<button class="btn" data-kind="quiet" data-act='${esc(JSON.stringify({ kind: 'DISMISS', alert_id: a.alert_id }))}'>${icon('x')} Dismiss</button>`;
    if (a.tier === 0) {
      const items = a.required_actions.map((r) => `
        <li data-done="${r.done ? 1 : 0}" class="${r.action === 'USE_SEALED_BACKUP' ? 'flag' : ''}">
          <span class="box">${r.done ? icon('check') : r.action === 'USE_SEALED_BACKUP' ? icon('warning') : ''}</span>
          ${icon(ACTION_ICON[r.action])} ${esc(r.label)}
          ${!r.done && r.carrier_id && ASSERT_LABEL[r.action] ? `<button class="btn small" data-kind="quiet" data-act='${esc(JSON.stringify({ kind: 'ASSERT_REPLACED', alert_id: a.alert_id, carrier_ids: [r.carrier_id] }))}'>${ASSERT_LABEL[r.action]}</button>` : ''}
        </li>`).join('');
      el.innerHTML = `<div class="label micro">Tier 0 · Reset prompt · Ticket ${esc(a.ticket_id)} · before you start</div>
        <div><h1 class="headline">${esc(a.headline)}</h1><ul class="checklist">${items}</ul></div>
        <div class="actions">${assertAll('ASSERT_REPLACED', 'All done — station reset', 'primary')}${dismiss}</div>`;
    } else if (a.tier === 1) {
      el.innerHTML = `<div class="label micro">Tier 1 · Interrupt · Ticket ${esc(a.ticket_id)}</div>
        <div><h1 class="headline">${esc(a.headline)}</h1>${a.body ? `<div class="body">${esc(a.body)}</div>` : ''}</div>
        <div class="actions">
          <button class="btn" data-kind="primary" data-act='${esc(JSON.stringify({ kind: 'ACKNOWLEDGE', alert_id: a.alert_id }))}'>${icon('arrows-clockwise')} ${esc(a.required_actions[0] ? a.required_actions[0].label : 'On it')}</button>
          ${assertAll('ASSERT_REPLACED', 'Already swapped', 'quiet')}${dismiss}</div>`;
    } else {
      el.innerHTML = `<div class="label micro">Tier 2 · Hold at the pass · Ticket ${esc(a.ticket_id)}</div>
        <div><h1 class="headline">${esc(a.headline)}</h1>${a.body ? `<div class="body">${esc(a.body)}</div>` : ''}<div class="trace">${traceLines(a.derivation)}</div></div>
        <div class="actions">
          ${assertAll('ASSERT_CLEAN', `Cook confirms ${a.required_actions.map((r) => r.label.toLowerCase()).join(', ') || 'tool'} was clean`, 'primary')}
          <button class="btn" data-kind="hold" data-act='${esc(JSON.stringify({ kind: 'REMAKE', ticket_id: a.ticket_id, alert_id: a.alert_id }))}'>${icon('arrow-counter-clockwise')} Remake</button></div>
        <div class="disclaimer">This is an observation, not a determination. Confirm with the cook.</div>`;
    }
  }

  function kv(rows) { return `<table class="kv">${rows.map((r) => `<tr>${r.map((c, i) => `<td class="${i ? 'mono' : ''}">${c}</td>`).join('')}</tr>`).join('')}</table>`; }
  function renderInspector(s) {
    $('mode-now').textContent = s.mode;
    $('carriers-table').innerHTML = `<table class="kv"><tr><th>carrier</th><th>kind</th><th>epistemic</th><th>seen</th><th>taints (grade · hops · via)</th></tr>${[...s.carriers].sort((a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind]).map((c) => `<tr><td class="mono">${esc(c.carrier_id)}</td><td>${c.kind}</td><td class="mono">${c.epistemic}</td><td class="mono">${fmtT(c.last_observed_at)}</td><td class="mono">${c.taints.map((t) => `${esc(t.allergen_id)} ${GRADE_ABBR[t.grade]} h${t.hops}${t.source_carrier_id ? ` ← ${esc(t.source_carrier_id)}` : ''} (${esc(t.source_event_id)})`).join('<br>') || '—'}</td></tr>`).join('')}</table>`;
    $('zones-count').textContent = s.zones.length;
    $('zones-table').innerHTML = `<table class="kv"><tr><th>zone</th><th>kind</th><th>contents</th><th>carrier</th><th>last contact</th></tr>${s.zones.map((z) => `<tr><td class="mono">${esc(z.zone_id)}</td><td>${z.kind}</td><td>${esc(z.contents.join(', ')) || '—'}</td><td class="mono">${esc(z.bound_carrier || '—')}</td><td class="mono">${fmtT(z.last_contact_at)}</td></tr>`).join('')}</table>`;
    const h = s.health;
    $('health-table').innerHTML = kv([['mode', s.mode], ['vision', h.vision], ['reasoning', h.reasoning], ['late rate', `${(h.late_rate * 100).toFixed(1)}%`], ['rejected events', h.rejected_events], ['last incident', esc(h.last_incident_event_id || '—')], ['message', esc(h.message || '—')], ['config / knowledge', `v${s.config_version} / v${s.knowledge_version}`], ['seq', s.seq], ['time', `${fmtT(s.time.t)} (${s.time.kind})`], ['multi-restriction', s.condition.multi_restriction]]);
    const sc = $('scrub');
    const max = s.recent_events.length ? s.recent_events[s.recent_events.length - 1].seq : 0;
    const atEnd = Number(sc.value) >= Number(sc.max);
    sc.max = max; if (atEnd) sc.value = max;
    $('scrub-val').textContent = sc.value;
    renderLog(s, Number(sc.value));
  }

  function render(s) {
    snap = s;
    renderTop(s); renderTickets(s); renderRisk(s);
    if (page === 'worker') { renderLog(s); renderGrid(s); renderSurface(s); }
    else renderInspector(s);
  }
  if (page === 'inspector') $('scrub').addEventListener('input', () => { if (snap) { $('scrub-val').textContent = $('scrub').value; renderLog(snap, Number($('scrub').value)); } });

  const params = new URLSearchParams(location.search);
  if (params.get('mock')) {
    fetch('/static/mock/snapshot.example.json').then((r) => r.json()).then(render);
    return;
  }
  function connect() {
    const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
    ws.onmessage = (m) => render(JSON.parse(m.data));
    ws.onclose = () => { $('banner').dataset.mode = 'DOWN'; $('banner-text').textContent = 'DISPLAY DISCONNECTED'; setTimeout(connect, 1000); };
  }
  connect();
})();
