// =====================================================================
// GOOGLE APPS SCRIPT - INSEAD AI Club Event 3 live poll (v2)
//
// ONE deploy serves BOTH polls and BOTH live pages.
//
// Two tabs in the one spreadsheet:
//   Poll1  -> [Timestamp, Name, Answer, Event]   (the one-word poll)
//   Poll2  -> [Timestamp, Name, Changed, Event]  (the yes/no "changed your mind")
// Each tab gets a bold, frozen header row created on first write.
//
// doPost routes on data.type:
//   'word'    -> Poll1   (default if type missing - backwards compatible)
//   'changed' -> Poll2
//
// doGet:
//   ?type=poll1 (default) | ?type=poll2  -> { status, count, responses:[...] }
//   ?callback=NAME present                -> JSONP: NAME({...}) as JavaScript,
//                                            so the static GitHub Pages results
//                                            page can read it cross-origin
//                                            (Apps Script cannot set CORS headers).
//
// One-time setup is in backend/DEPLOY.md - follow it top to bottom.
// =====================================================================

// ---- Tab definitions -------------------------------------------------
var POLL1 = {
  tab: 'Poll1',
  headers: ['Timestamp', 'Name', 'Answer', 'Event'],
  keys: ['timestamp', 'name', 'answer', 'event']
};
var POLL2 = {
  tab: 'Poll2',
  headers: ['Timestamp', 'Name', 'Changed', 'Event'],
  keys: ['timestamp', 'name', 'changed', 'event']
};

// Pick the tab config from a 'type' value (front-end sends 'word' or 'changed').
function configForType(type) {
  if (type === 'changed' || type === 'poll2') return POLL2;
  return POLL1; // 'word', 'poll1', undefined -> Poll1 (backwards compatible)
}

// Get (creating if needed) a tab, with a bold + frozen header row.
function getSheet(cfg) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(cfg.tab);
  if (!sheet) {
    sheet = ss.insertSheet(cfg.tab);
  }
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(cfg.headers);
    sheet.getRange(1, 1, 1, cfg.headers.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
  }
  return sheet;
}

// -------- WRITE: phone submits -> append a row to the right tab --------
function doPost(e) {
  var data = JSON.parse(e.postData.contents);
  var cfg = configForType(data.type);
  var sheet = getSheet(cfg);

  var row = cfg.keys.map(function (key) {
    return data[key] !== undefined ? data[key] : '';
  });
  sheet.appendRow(row);

  return ContentService
    .createTextOutput(JSON.stringify({ status: 'ok', tab: cfg.tab }))
    .setMimeType(ContentService.MimeType.JSON);
}

// -------- READ: GET returns one tab's responses as JSON (or JSONP) ----
function doGet(e) {
  var params = (e && e.parameter) ? e.parameter : {};
  var type = params.type || 'poll1';
  var cfg = configForType(type);

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(cfg.tab);

  var responses = [];
  if (sheet) {
    var lastRow = sheet.getLastRow();
    if (lastRow > 1) {
      var values = sheet.getRange(2, 1, lastRow - 1, cfg.headers.length).getValues();
      for (var i = 0; i < values.length; i++) {
        var r = values[i];
        var obj = {};
        for (var c = 0; c < cfg.keys.length; c++) {
          obj[cfg.keys[c]] = r[c];
        }
        responses.push(obj);
      }
    }
  }

  var out = {
    status: 'ok',
    service: 'event-three poll',
    type: (cfg === POLL2) ? 'poll2' : 'poll1',
    count: responses.length,
    responses: responses
  };

  var json = JSON.stringify(out);

  // JSONP: if a callback name is supplied, wrap the JSON in a function call
  // and serve it as JavaScript so a cross-origin browser page can read it.
  var callback = params.callback;
  if (callback) {
    // Only allow a safe JS identifier as the callback name.
    var safe = /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(callback) ? callback : 'callback';
    return ContentService
      .createTextOutput(safe + '(' + json + ');')
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }

  return ContentService
    .createTextOutput(json)
    .setMimeType(ContentService.MimeType.JSON);
}
