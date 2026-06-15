// =====================================================================
// GOOGLE APPS SCRIPT - INSEAD AI Club Event 3 live poll
//
// Reuses the proven Event 1 / poll pattern (doPost appends a row to a
// Google Sheet), and ADDS a doGet that returns every response as JSON
// so the local takeaway generator can fetch results with one command.
//
// One-time setup is in backend/DEPLOY.md - follow it top to bottom.
// =====================================================================

// Column headers (the Sheet's first row)
const HEADERS = ['Timestamp', 'Name', 'Answer', 'Event'];

// Payload keys in the SAME order as HEADERS
const KEYS = ['timestamp', 'name', 'answer', 'event'];

// -------- WRITE: phone submits a {name, answer} -> append a row --------
function doPost(e) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  // Add the header row the first time
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(HEADERS);
    sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
  }

  const data = JSON.parse(e.postData.contents);
  const row = KEYS.map(function (key) {
    return data[key] !== undefined ? data[key] : '';
  });
  sheet.appendRow(row);

  return ContentService
    .createTextOutput(JSON.stringify({ status: 'ok' }))
    .setMimeType(ContentService.MimeType.JSON);
}

// -------- READ: GET returns all responses as JSON --------
// Plain GET  -> { status:'ok', count:N, responses:[{timestamp,name,answer,event}, ...] }
// This is what poll_takeaway.py calls at the end of the talk.
function doGet(e) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const lastRow = sheet.getLastRow();

  const responses = [];
  if (lastRow > 1) {
    // rows 2..lastRow, columns 1..HEADERS.length (skip the header row)
    const values = sheet.getRange(2, 1, lastRow - 1, HEADERS.length).getValues();
    for (var i = 0; i < values.length; i++) {
      var r = values[i];
      responses.push({
        timestamp: r[0],
        name: r[1],
        answer: r[2],
        event: r[3]
      });
    }
  }

  return ContentService
    .createTextOutput(JSON.stringify({
      status: 'ok',
      service: 'event-three poll',
      count: responses.length,
      responses: responses
    }))
    .setMimeType(ContentService.MimeType.JSON);
}
