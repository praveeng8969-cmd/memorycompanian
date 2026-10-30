"use strict";

const $ = id => document.getElementById(id);
let dashboard = null;

// Centralized Level Configurations matching Backend/policy.py
const LEVEL_CONFIG = {
  1: { level: 1, name: "Gentle", pairs_per_board: 3, total_boards: 2, description: "3 pairs/board · 2 boards (up to 6 pair attempts)" },
  2: { level: 2, name: "Steady", pairs_per_board: 4, total_boards: 2, description: "4 pairs/board · 2 boards (up to 8 pair attempts)" },
  3: { level: 3, name: "More pairs", pairs_per_board: 5, total_boards: 1, description: "5 pairs/board · 1 board (up to 5 pair attempts)" }
};

// Familiar North-East Region & everyday cultural object pools
const FAMILIAR_OBJECTS_POOL_1 = ['Tea cup', 'Garden', 'Family', 'House', 'Flower', 'Bamboo grove'];
const FAMILIAR_OBJECTS_POOL_2 = ['River', 'Clay lamp', 'Fresh fruit', 'Warm shawl', 'Morning sun', 'Singing bird'];

// Robust Clean Game State Model
const game = {
  active: false,
  state: 'idle', // 'idle' | 'playing' | 'resolving_pair' | 'hinting' | 'board_completed' | 'paused' | 'saving' | 'completed'
  clientSessionId: null,
  level: 1,
  pairsPerBoard: 3,
  totalBoards: 2,
  currentBoard: 1,
  totalCorrect: 0,
  totalAttempts: 0,
  totalHints: 0,
  boardCorrect: 0,
  cards: [],
  selectedCard: null,
  timers: []
};

function clearGameTimers() {
  game.timers.forEach(t => clearTimeout(t));
  game.timers = [];
}

function status(text, error = false) {
  const el = $('status');
  el.textContent = text;
  el.classList.toggle('error', error);
}

async function api(path, body) {
  const options = body === undefined
    ? { headers: { 'Cache-Control': 'no-store' } }
    : {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
        body: JSON.stringify(body)
      };
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Request failed with status ${res.status}`);
  }
  return data;
}

function show(view) {
  document.querySelectorAll('main > section').forEach(s => s.hidden = s.id !== view);
  document.querySelectorAll('nav button').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('[data-view]').forEach(b => {
  b.onclick = () => show(b.dataset.view);
});

function say(text) {
  if ($('voice').checked && 'speechSynthesis' in window) {
    try {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      speechSynthesis.speak(utterance);
    } catch (e) {
      // Speech is strictly optional with graceful fallback
    }
  }
}

function feedback(text) {
  $('feedback').textContent = text;
  say(text);
}

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined && text !== '') el.textContent = text;
  if (className) el.className = className;
  return el;
}

// -------------------------------------------------------------
// DASHBOARD & STATE SYNCHRONIZATION
// -------------------------------------------------------------
async function load() {
  dashboard = await api('/api/dashboard');

  // 1. Participant Greeting & Profile Form
  status(`Welcome, ${dashboard.profile.name}. Your activity stays safely on this device.`);
  const pf = $('profile-form').elements;
  pf.name.value = dashboard.profile.name;
  pf.consent.checked = !!dashboard.profile.consent;
  if (pf.auto_apply_plan) {
    pf.auto_apply_plan.checked = !!dashboard.profile.auto_apply_plan;
  }

  // 2. Render Next Activity Plan on Home & Game Views
  renderNextPlanCards();

  // 3. Render Memory Book (Approved Only in Participant View)
  renderMemoryBook();

  // 4. Render Reminders (Participant View)
  renderReminders();

  // 5. Render Caregiver Workspace (Supervision, Management & Table)
  renderCaregiverWorkspace();
}

function renderNextPlanCards() {
  const plan = dashboard.next_plan;
  if (!plan) return;

  const cfg = LEVEL_CONFIG[plan.target_level] || LEVEL_CONFIG[1];
  const isApproved = (plan.status === 'approved' || plan.status === 'overridden');

  // HOME Plan Card
  const homeBadge = $('home-plan-badge');
  homeBadge.textContent = isApproved ? 'Ready to play' : 'Caregiver review required';
  homeBadge.className = 'badge ' + (isApproved ? 'badge-ready' : 'badge-pending');

  $('home-plan-level').textContent = `Level ${plan.target_level} · ${cfg.name}`;
  $('home-plan-title').textContent = `Your Next Activity: ${plan.activity_name}`;
  $('home-plan-config').textContent = `${plan.pairs_per_board} pairs per board · ${plan.total_boards} planned board${plan.total_boards > 1 ? 's' : ''}`;
  $('home-plan-reason').textContent = plan.reason;

  const homeBtn = $('home-plan-btn');
  if (isApproved) {
    homeBtn.textContent = 'Start next activity';
    homeBtn.onclick = () => {
      show('game');
      startPlannedActivity(plan.target_level);
    };
  } else {
    homeBtn.textContent = 'Ask your caregiver to review';
    homeBtn.onclick = () => show('caregiver');
  }

  // GAME Plan Banner
  const gameBadge = $('game-plan-badge');
  gameBadge.textContent = isApproved ? 'Approved Plan' : 'Pending Review';
  gameBadge.className = 'badge ' + (isApproved ? 'badge-approved' : 'badge-pending');

  $('game-plan-level-text').textContent = `Level ${plan.target_level} (${cfg.name})`;
  $('game-plan-boards-text').textContent = `${plan.total_boards} board${plan.total_boards > 1 ? 's' : ''} planned (${plan.pairs_per_board} pairs each)`;
  $('game-plan-reason-text').textContent = plan.reason;

  // Sync Level dropdown if not active
  if (!game.active) {
    $('level').value = String(plan.target_level);
  }
}

function renderMemoryBook() {
  const book = $('memory-list');
  book.replaceChildren();
  const approved = dashboard.memories.filter(m => m.approved);
  approved.forEach(m => {
    const a = node('article', '');
    const title = node('h2', m.title);
    const desc = node('p', m.description);
    a.append(title, desc);
    book.append(a);
  });
  if (!approved.length) {
    book.append(node('p', 'Your caregiver can add familiar moments and stories here.'));
  }
}

function renderReminders() {
  if (!dashboard) return;
  const list = $('reminder-list');
  list.replaceChildren();

  dashboard.reminders.forEach(r => {
    const a = node('article', '', 'reminder' + (r.acknowledged ? ' acknowledged' : ''));
    const when = new Date(r.due_at);
    const isDue = !r.acknowledged && when <= new Date();
    if (isDue) a.classList.add('due');

    const div = document.createElement('div');
    div.append(
      node('h2', r.title),
      node('p', `${when.toLocaleString()}${isDue ? ' · Due now' : ''}`)
    );
    a.append(div);

    if (r.acknowledged) {
      const ackDate = r.acknowledged_at ? new Date(r.acknowledged_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
      a.append(node('span', `Acknowledged ${ackDate}`, 'badge-ack'));
    } else {
      const btn = node('button', 'Mark done', 'btn-primary');
      btn.onclick = async () => {
        btn.disabled = true;
        try {
          await api(`/api/reminders/${r.id}/acknowledge`, {});
          await load();
          feedback(`Thank you. You acknowledged: ${r.title}`);
        } catch (err) {
          status(err.message, true);
          btn.disabled = false;
        }
      };
      a.append(btn);
    }
    list.append(a);
  });

  if (!dashboard.reminders.length) {
    list.append(node('p', 'No reminders scheduled. Your caregiver can add daily reminders for you.'));
  }
}
setInterval(renderReminders, 30000);

function renderCaregiverWorkspace() {
  const plan = dashboard.next_plan;
  const cfg = LEVEL_CONFIG[plan.target_level] || LEVEL_CONFIG[1];

  // Supervision card
  const statusEl = $('caregiver-plan-status');
  statusEl.textContent = plan.status.toUpperCase();
  statusEl.className = 'badge ' + (plan.status === 'approved' ? 'badge-approved' : plan.status === 'overridden' ? 'badge-overridden' : 'badge-pending');

  $('caregiver-plan-level').textContent = `Level ${plan.target_level} (${cfg.name})`;
  $('caregiver-plan-config').textContent = `${plan.pairs_per_board} pairs per board · ${plan.total_boards} planned board${plan.total_boards > 1 ? 's' : ''}`;
  $('caregiver-plan-reason').textContent = plan.reason;
  $('caregiver-policy-reason').textContent = plan.caregiver_reason || 'Initial activity baseline.';

  const latestSession = dashboard.sessions[0];
  $('caregiver-model-prediction').textContent = latestSession && latestSession.model_action
    ? latestSession.model_action.toUpperCase()
    : 'Not available (requires >= 5 pair attempts in session)';

  $('model-state').textContent = dashboard.model_loaded
    ? 'Trained Random Forest demonstration pipeline loaded.'
    : 'Rule policy active. Model pipeline optional.';

  const approveBtn = $('approve-plan-btn');
  approveBtn.disabled = (plan.status === 'approved' || plan.status === 'overridden' || game.active);
  approveBtn.onclick = async () => {
    approveBtn.disabled = true;
    try {
      await api('/api/plan/approve', {});
      await load();
      status('Caregiver approved the next activity plan.');
    } catch (err) {
      status(err.message, true);
      approveBtn.disabled = false;
    }
  };

  // Memories Management List
  const memList = $('caregiver-memories-list');
  memList.replaceChildren();
  dashboard.memories.forEach(m => {
    const item = node('div', '', 'manage-item');
    const info = document.createElement('div');
    info.append(
      node('strong', m.title),
      document.createElement('br'),
      node('span', m.description, 'plan-subtext'),
      document.createElement('br'),
      node('span', m.approved ? 'Approved for participant' : 'Hidden from participant', 'badge ' + (m.approved ? 'badge-approved' : 'badge-pending'))
    );

    const actions = node('div', '', 'manage-actions');
    const editBtn = node('button', 'Edit', 'btn-secondary');
    editBtn.onclick = () => openEditMemoryDialog(m);

    const toggleBtn = node('button', m.approved ? 'Hide' : 'Approve', 'btn-secondary');
    toggleBtn.onclick = async () => {
      toggleBtn.disabled = true;
      try {
        await api(`/api/memories/${m.id}/update`, { title: m.title, description: m.description, approved: !m.approved });
        await load();
      } catch (e) {
        status(e.message, true);
        toggleBtn.disabled = false;
      }
    };

    const delBtn = node('button', 'Delete', 'btn-danger');
    delBtn.onclick = async () => {
      if (!confirm(`Delete memory "${m.title}"?`)) return;
      delBtn.disabled = true;
      try {
        await api(`/api/memories/${m.id}/delete`, {});
        await load();
      } catch (e) {
        status(e.message, true);
        delBtn.disabled = false;
      }
    };

    actions.append(editBtn, toggleBtn, delBtn);
    item.append(info, actions);
    memList.append(item);
  });
  if (!dashboard.memories.length) {
    memList.append(node('p', 'No memories added yet.'));
  }

  // Reminders Management List
  const remList = $('caregiver-reminders-list');
  remList.replaceChildren();
  dashboard.reminders.forEach(r => {
    const item = node('div', '', 'manage-item');
    const when = new Date(r.due_at);
    const isDue = !r.acknowledged && when <= new Date();

    const info = document.createElement('div');
    info.append(
      node('strong', r.title),
      document.createElement('br'),
      node('span', `Due: ${when.toLocaleString()}${isDue ? ' (Due now)' : ''}`, 'plan-subtext'),
      document.createElement('br'),
      node('span', r.acknowledged ? 'Acknowledged' : 'Pending', 'badge ' + (r.acknowledged ? 'badge-approved' : 'badge-pending'))
    );

    const actions = node('div', '', 'manage-actions');
    const editBtn = node('button', 'Edit', 'btn-secondary');
    editBtn.onclick = () => openEditReminderDialog(r);

    const delBtn = node('button', 'Delete', 'btn-danger');
    delBtn.onclick = async () => {
      if (!confirm(`Delete reminder "${r.title}"?`)) return;
      delBtn.disabled = true;
      try {
        await api(`/api/reminders/${r.id}/delete`, {});
        await load();
      } catch (e) {
        status(e.message, true);
        delBtn.disabled = false;
      }
    };

    actions.append(editBtn, delBtn);
    item.append(info, actions);
    remList.append(item);
  });
  if (!dashboard.reminders.length) {
    remList.append(node('p', 'No reminders added yet.'));
  }

  // History Table
  const tbody = $('history');
  tbody.replaceChildren();
  dashboard.sessions.forEach(s => {
    const tr = document.createElement('tr');
    const localTime = new Date(s.created_at).toLocaleString();
    const boards = s.boards_completed && s.total_boards ? `${s.boards_completed} / ${s.total_boards}` : '1 / 1';
    [
      localTime,
      `Level ${s.level}`,
      boards,
      `${s.correct} / ${s.attempts}`,
      s.hints,
      s.status || (s.paused ? 'paused' : 'completed'),
      s.recommendation.replaceAll('_', ' '),
      s.reason || 'Standard activity',
      s.model_action || 'Not available'
    ].forEach(text => tr.append(node('td', text)));
    tbody.append(tr);
  });
}

// -------------------------------------------------------------
// ADAPTIVE MATCHING GAME IMPLEMENTATION (MULTI-BOARD & STATE)
// -------------------------------------------------------------
function shuffle(array) {
  const arr = [...array];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function updateGameControls() {
  const isPlaying = (game.state === 'playing');
  const isPaused = (game.state === 'paused');
  const isSaving = (game.state === 'saving');
  const isBoardDone = (game.state === 'board_completed');

  $('start').disabled = game.active;
  $('level').disabled = game.active;
  $('hint').disabled = !isPlaying;
  $('pause').disabled = (!isPlaying && !isPaused) || isSaving;
  $('finish').disabled = !game.active || isSaving;
  $('resume').hidden = !isPaused;
  $('continue-board').hidden = !isBoardDone;

  const pauseBtn = $('pause');
  if (isPaused) {
    pauseBtn.textContent = 'Save paused activity';
  } else {
    pauseBtn.textContent = 'Pause activity';
  }

  const indicator = $('board-indicator');
  if (game.active) {
    indicator.hidden = false;
    $('board-number-text').textContent = `Board ${game.currentBoard} of ${game.totalBoards}`;
    $('board-pairs-text').textContent = `${game.pairsPerBoard} pairs (${game.boardCorrect} found)`;
  } else {
    indicator.hidden = true;
  }
}

function renderCards() {
  const wrap = $('cards');
  wrap.replaceChildren();

  game.cards.forEach((card, index) => {
    const btn = node('button', card.matched || card.revealed ? card.label : '?');
    btn.className = 'card' + (card.matched ? ' matched' : '') + (card.revealed ? ' revealed' : '');
    btn.setAttribute('aria-label', card.matched ? `Matched ${card.label}` : card.revealed ? card.label : `Face down card ${index + 1}`);
    btn.disabled = card.matched || (game.state !== 'playing');
    btn.onclick = () => chooseCard(index);
    wrap.append(btn);
  });

  $('game-info').textContent = `Level ${game.level} · Board ${game.currentBoard}/${game.totalBoards} · Total pairs found: ${game.totalCorrect} · Attempts: ${game.totalAttempts} · Hints: ${game.totalHints}`;
  updateGameControls();
}

function setupBoard(boardNumber) {
  clearGameTimers();
  game.currentBoard = boardNumber;
  game.boardCorrect = 0;
  game.selectedCard = null;

  // Pick familiar cultural objects suitable for board
  const pool = (boardNumber % 2 === 1) ? FAMILIAR_OBJECTS_POOL_1 : FAMILIAR_OBJECTS_POOL_2;
  const labels = pool.slice(0, game.pairsPerBoard);

  const cardList = labels.flatMap(label => [
    { label, matched: false, revealed: false },
    { label, matched: false, revealed: false }
  ]);
  game.cards = shuffle(cardList);
  game.state = 'playing';
  renderCards();
}

function startPlannedActivity(level) {
  const chosenLevel = maxLevel(level || Number($('level').value));
  const cfg = LEVEL_CONFIG[chosenLevel] || LEVEL_CONFIG[1];

  clearGameTimers();
  Object.assign(game, {
    active: true,
    state: 'playing',
    clientSessionId: 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 9),
    level: chosenLevel,
    pairsPerBoard: cfg.pairs_per_board,
    totalBoards: cfg.total_boards,
    currentBoard: 1,
    totalCorrect: 0,
    totalAttempts: 0,
    totalHints: 0,
    boardCorrect: 0,
    cards: [],
    selectedCard: null
  });

  $('level').value = String(chosenLevel);
  setupBoard(1);
  feedback(`Level ${chosenLevel} activity started. Board 1 of ${cfg.total_boards}. Find two matching cards.`);
}

function maxLevel(lvl) {
  return Math.max(1, Math.min(3, Number(lvl) || 1));
}

$('start').onclick = () => {
  if (game.active) return;
  startPlannedActivity(Number($('level').value));
};

function chooseCard(index) {
  if (game.state !== 'playing') return;
  const card = game.cards[index];
  if (card.matched || card.revealed || game.selectedCard === index) return;

  card.revealed = true;
  say(card.label);

  if (game.selectedCard === null) {
    game.selectedCard = index;
    renderCards();
    return;
  }

  // Exactly two distinct unmatched cards selected = One valid attempt
  const firstIndex = game.selectedCard;
  game.totalAttempts++;
  game.selectedCard = null;

  const firstCard = game.cards[firstIndex];
  if (firstCard.label === card.label) {
    // MATCH FOUND
    firstCard.matched = true;
    card.matched = true;
    game.totalCorrect++;
    game.boardCorrect++;

    if (game.boardCorrect === game.pairsPerBoard) {
      if (game.currentBoard < game.totalBoards) {
        game.state = 'board_completed';
        feedback(`Well done! Board ${game.currentBoard} completed. Continue to the next board whenever you are ready.`);
      } else {
        game.state = 'completed';
        feedback('All boards completed! Finish and save your activity when you are ready.');
      }
    } else {
      feedback('Good match. Take your time.');
    }
    renderCards();
  } else {
    // MISMATCH
    game.state = 'resolving_pair';
    renderCards();
    feedback('These are different. You can try again.');

    const timer = setTimeout(() => {
      firstCard.revealed = false;
      card.revealed = false;
      game.state = 'playing';
      renderCards();
    }, 1200);
    game.timers.push(timer);
  }
}

// Continue to next planned board
$('continue-board').onclick = () => {
  if (game.state !== 'board_completed') return;
  const nextBoard = game.currentBoard + 1;
  setupBoard(nextBoard);
  feedback(`Board ${nextBoard} of ${game.totalBoards} ready. Choose two cards to find a pair.`);
};

// Hint Feature
$('hint').onclick = () => {
  if (game.state !== 'playing') return;
  const unmatched = game.cards.find(c => !c.matched);
  if (!unmatched) return;

  game.totalHints++;
  game.state = 'hinting';
  game.selectedCard = null;

  game.cards.forEach(c => {
    c.revealed = c.matched || (c.label === unmatched.label);
  });
  renderCards();
  feedback(`Look for the two cards named ${unmatched.label}.`);

  const timer = setTimeout(() => {
    game.cards.forEach(c => {
      c.revealed = c.matched;
    });
    game.state = 'playing';
    renderCards();
  }, 2000);
  game.timers.push(timer);
};

// Pause / Save Handler
$('pause').onclick = async () => {
  if (!game.active) return;

  if (game.state === 'paused') {
    // Saving paused activity
    await saveSession(true);
    return;
  }

  // Enter Pause
  clearGameTimers();
  game.selectedCard = null;
  game.cards.forEach(c => {
    c.revealed = c.matched;
  });
  game.state = 'paused';
  renderCards();
  feedback('Activity paused. Take a rest. You can resume, or save this paused activity.');
};

$('resume').onclick = () => {
  if (game.state !== 'paused') return;
  game.state = 'playing';
  renderCards();
  feedback('Welcome back. Continue finding pairs at your own pace.');
};

$('finish').onclick = () => saveSession(false);

async function saveSession(isPaused) {
  if (!game.active || game.state === 'saving') return;
  clearGameTimers();

  const prevState = game.state;
  game.state = 'saving';
  updateGameControls();

  const payload = {
    client_session_id: game.clientSessionId,
    correct: game.totalCorrect,
    attempts: game.totalAttempts,
    hints: game.totalHints,
    level: game.level,
    paused: isPaused,
    boards_completed: game.currentBoard,
    total_boards: game.totalBoards
  };

  try {
    const res = await api('/api/sessions', payload);
    game.active = false;
    game.state = 'idle';
    feedback(`${res.reason} Activity saved. Next activity plan is ready.`);
    await load();
  } catch (err) {
    status(err.message, true);
    // Restore state so participant can retry save
    game.state = prevState;
    updateGameControls();
  } finally {
    renderCards();
  }
}

// -------------------------------------------------------------
// CAREGIVER OVERRIDE & FORMS
// -------------------------------------------------------------
$('profile-form').onsubmit = async e => {
  e.preventDefault();
  const f = e.target.elements;
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try {
    await api('/api/profile', {
      name: f.name.value,
      consent: f.consent.checked,
      auto_apply_plan: f.auto_apply_plan ? f.auto_apply_plan.checked : false
    });
    await load();
    status('Profile and permissions saved successfully.');
  } catch (err) {
    status(err.message, true);
  } finally {
    btn.disabled = false;
  }
};

$('override-form').onsubmit = async e => {
  e.preventDefault();
  if (game.active) {
    status('Please finish or pause the active session before applying a caregiver override.', true);
    return;
  }
  const f = e.target.elements;
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try {
    await api('/api/plan/override', {
      level: Number(f.override_level.value),
      reason: f.override_reason.value
    });
    await load();
    status('Caregiver override applied to next activity plan.');
  } catch (err) {
    status(err.message, true);
  } finally {
    btn.disabled = false;
  }
};

$('memory-form').onsubmit = async e => {
  e.preventDefault();
  const f = e.target.elements;
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try {
    await api('/api/memories', {
      title: f.title.value,
      description: f.description.value,
      approved: f.approved.checked
    });
    e.target.reset();
    f.approved.checked = true;
    await load();
    status('New memory added successfully.');
  } catch (err) {
    status(err.message, true);
  } finally {
    btn.disabled = false;
  }
};

$('reminder-form').onsubmit = async e => {
  e.preventDefault();
  const f = e.target.elements;
  const btn = e.target.querySelector('button');
  btn.disabled = true;
  try {
    await api('/api/reminders', {
      title: f.title.value,
      due_at: f.due_at.value
    });
    e.target.reset();
    await load();
    status('Reminder added successfully.');
  } catch (err) {
    status(err.message, true);
  } finally {
    btn.disabled = false;
  }
};

$('seed-memories-btn').onclick = async () => {
  const btn = $('seed-memories-btn');
  btn.disabled = true;
  try {
    const samples = [
      { title: "Family Tea Time", description: "Remembering our gentle morning tea together on the front porch with warm chai.", approved: true },
      { title: "Lush Green Hills", description: "The morning mist rising softly over the quiet tea gardens and bamboo groves.", approved: true },
      { title: "Garden Marigolds", description: "Bright orange and yellow flowers blooming by the courtyard gate.", approved: true }
    ];
    for (const m of samples) {
      await api('/api/memories', m);
    }
    await load();
    status('Sample familiar memories loaded.');
  } catch (err) {
    status(err.message, true);
  } finally {
    btn.disabled = false;
  }
};

// -------------------------------------------------------------
// EDIT DIALOGS (MEMORIES & REMINDERS)
// -------------------------------------------------------------
function openEditMemoryDialog(m) {
  const dlg = $('edit-memory-dialog');
  const f = $('edit-memory-form').elements;
  f.id.value = m.id;
  f.title.value = m.title;
  f.description.value = m.description;
  f.approved.checked = !!m.approved;
  dlg.showModal();
}

$('close-memory-dialog').onclick = () => $('edit-memory-dialog').close();

$('edit-memory-form').onsubmit = async e => {
  e.preventDefault();
  const f = e.target.elements;
  const btn = e.target.querySelector('button[type=submit]');
  btn.disabled = true;
  try {
    await api(`/api/memories/${f.id.value}/update`, {
      title: f.title.value,
      description: f.description.value,
      approved: f.approved.checked
    });
    $('edit-memory-dialog').close();
    await load();
    status('Memory updated successfully.');
  } catch (err) {
    status(err.message, true);
  } finally {
    btn.disabled = false;
  }
};

function openEditReminderDialog(r) {
  const dlg = $('edit-reminder-dialog');
  const f = $('edit-reminder-form').elements;
  f.id.value = r.id;
  f.title.value = r.title;
  // Convert local ISO for input
  const date = new Date(r.due_at);
  const pad = n => String(n).padStart(2, '0');
  const localIso = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  f.due_at.value = localIso;
  dlg.showModal();
}

$('close-reminder-dialog').onclick = () => $('edit-reminder-dialog').close();

$('edit-reminder-form').onsubmit = async e => {
  e.preventDefault();
  const f = e.target.elements;
  const btn = e.target.querySelector('button[type=submit]');
  btn.disabled = true;
  try {
    await api(`/api/reminders/${f.id.value}/update`, {
      title: f.title.value,
      due_at: f.due_at.value
    });
    $('edit-reminder-dialog').close();
    await load();
    status('Reminder updated successfully.');
  } catch (err) {
    status(err.message, true);
  } finally {
    btn.disabled = false;
  }
};

// -------------------------------------------------------------
// INITIALIZATION
// -------------------------------------------------------------
show('home');
load().catch(e => status(e.message, true));
