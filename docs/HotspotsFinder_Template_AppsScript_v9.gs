// ============================================================
// HOTSPOTS FINDER - BOUND APPS SCRIPT v9
//
// PRINCIPIO:
// Apps Script protegge soltanto la STRUTTURA FUNZIONALE.
// La grafica resta libera e personalizzabile dall'utente.
//
// Python / Desktop App resta responsabile di:
// - Repair Sheet completo
// - Restore Official Style
// - Save Current Style
// - resize colonne
// - query Spansh e scrittura risultati
//
// Apps Script protegge:
// - etichette A1:A28
// - checkbox funzionali in colonna B
// - Faction come input libero
// - Power B20 come dropdown strutturale protetto
//   (se la regola è già corretta, non viene ricreata)
// - Status B28
// - Systems / Total
// - intestazioni risultati riga 1
// - formato delle sole aree protette dopo un probabile incolla multiplo
//
// Apps Script NON ripara automaticamente:
// - sfondi
// - bordi
// - font
// - dimensione font
// - colore testo
// - allineamenti
// - formati numerici
// - larghezze colonne
// - altezze righe
//
// Eccezione:
// dopo un probabile incolla multiplo, il formato delle sole aree
// funzionali protette viene ripristinato dal template _HF_STYLE.
// ============================================================

const HF_SHEET_NAME = "Hotspots Finder";
const HF_STYLE_SHEET = "_HF_STYLE";

const HF_POWERS = [
  "Aisling Duval",
  "Archon Delaine",
  "Arissa Lavigny-Duval",
  "Denton Patreus",
  "Edmund Mahon",
  "Felicia Winters",
  "Jerome Archer",
  "Li Yong-Rui",
  "Nakato Kaine",
  "Pranav Antal",
  "Yuri Grom",
  "Zemina Torval",
];


// ------------------------------------------------------------
// SIMPLE TRIGGERS
// ------------------------------------------------------------

function onOpen() {
  const sheet =
    getHotspotsSheet_();

  if (sheet) {
    repairPowerDropdown_(
      sheet
    );
  }

  SpreadsheetApp
    .getUi()
    .createMenu("Hotspots Finder")
    .addItem(
      "Repair protected structure",
      "repairProtectedStructure"
    )
    .addItem(
      "Update Total",
      "updateSystemsCounter"
    )
    .addToUi();
}


function onEdit(e) {
  if (!e || !e.range) {
    return;
  }

  const sheet =
    e.range.getSheet();

  if (
    sheet.getName() !==
    HF_SHEET_NAME
  ) {
    return;
  }

  const edited =
    e.range;

  // --------------------------------------------------------
  // A1:A28 = fixed labels / filter titles
  // --------------------------------------------------------

  if (
    intersects_(
      edited,
      1, 1,
      28, 1
    )
  ) {
    restoreFilterLabels_(
      sheet
    );
  }

  // --------------------------------------------------------
  // B column = functional controls
  // --------------------------------------------------------

  if (
    intersectsAny_(
      edited,
      [
        [1, 2, 9, 2],
        [11, 2, 17, 2],
        [21, 2, 24, 2],
        [26, 2, 26, 2]
      ]
    )
  ) {
    repairCheckboxes_(
      sheet
    );
  }

  // Spacer cells must remain empty.
  if (
    intersectsAny_(
      edited,
      [
        [10, 2, 10, 2],
        [18, 2, 18, 2],
        [25, 2, 25, 2],
        [27, 2, 27, 2]
      ]
    )
  ) {
    clearFilterSpacerCells_(
      sheet
    );
  }

  // B19 = Faction name -> free user input.

  // B20 = Power -> protected dropdown, free visual style.
  if (
    intersects_(
      edited,
      20, 2,
      20, 2
    )
  ) {
    repairPowerDropdown_(
      sheet
    );
  }

  // B28 = application status
  if (
    intersects_(
      edited,
      28, 2,
      28, 2
    )
  ) {
    repairStatusValue_(
      sheet
    );
  }

  // --------------------------------------------------------
  // Systems + Total
  // --------------------------------------------------------

  if (
    intersects_(
      edited,
      1, 3,
      1, 4
    )
  ) {
    restoreSystemsHeaders_(
      sheet
    );

    updateSystemsCounter_(
      sheet
    );
  }

  if (
    intersects_(
      edited,
      2, 3,
      sheet.getMaxRows(), 3
    )
  ) {
    updateSystemsCounter_(
      sheet
    );
  }

  // --------------------------------------------------------
  // Result headers / separator
  // --------------------------------------------------------

  if (
    intersects_(
      edited,
      1, 5,
      1, 21
    )
  ) {
    restoreResultHeaders_(
      sheet
    );
  }

  // --------------------------------------------------------
  // Likely multi-cell paste:
  // repair formatting ONLY in protected functional areas.
  //
  // Google Apps Script has no reliable clipboard flag.
  // A multi-cell edit is therefore treated as a likely paste.
  // --------------------------------------------------------

  if (
    isLikelyMultiCellPaste_(
      e
    )
  ) {
    repairProtectedPasteFormatting_(
      sheet,
      edited
    );
  }
}


// ------------------------------------------------------------
// PUBLIC MENU FUNCTIONS
// ------------------------------------------------------------

function repairProtectedStructure() {
  const sheet =
    getHotspotsSheet_();

  if (!sheet) {
    return;
  }

  restoreFilterLabels_(
    sheet
  );

  repairCheckboxes_(
    sheet
  );

  repairPowerDropdown_(
    sheet
  );

  clearFilterSpacerCells_(
    sheet
  );

  repairStatusValue_(
    sheet
  );

  restoreSystemsHeaders_(
    sheet
  );

  restoreResultHeaders_(
    sheet
  );

  updateSystemsCounter_(
    sheet
  );

  SpreadsheetApp.flush();
}


function updateSystemsCounter() {
  const sheet =
    getHotspotsSheet_();

  if (!sheet) {
    return;
  }

  updateSystemsCounter_(
    sheet
  );
}


// ------------------------------------------------------------
// FIXED FILTER LABELS
// ------------------------------------------------------------

function restoreFilterLabels_(
  sheet
) {
  const labels = [
    ["Hotspots"],
    ["Icy"],
    ["Metallic"],
    ["Metal Rich"],
    ["Rocky"],
    ["Platinum"],
    ["Bromellite"],
    ["Monazite"],
    ["Only pristine"],
    [""],
    ["Planets"],
    ["Only landables"],
    ["Icy"],
    ["Metal Rich"],
    ["High Metal Content"],
    ["Rocky"],
    ["Rocky Ice"],
    [""],
    ["Faction name"],
    ["Power"],
    ["Unoccupied"],
    ["Exploited"],
    ["Fortified"],
    ["Stronghold"],
    [""],
    ["Only positive results"],
    [""],
    ["Status"]
  ];

  sheet
    .getRange("A1:A28")
    .setValues(labels);
}


// ------------------------------------------------------------
// CHECKBOXES
// ------------------------------------------------------------

function repairCheckboxes_(
  sheet
) {
  const rule =
    SpreadsheetApp
      .newDataValidation()
      .requireCheckbox()
      .setAllowInvalid(false)
      .build();

  const ranges = [
    "B1:B9",
    "B11:B17",
    "B21:B24",
    "B26"
  ];

  ranges.forEach(
    function(a1) {
      const range =
        sheet.getRange(a1);

      const values =
        range.getValues();

      for (
        let r = 0;
        r < values.length;
        r++
      ) {
        const value =
          values[r][0];

        // Preserve actual checkbox values.
        // Invalid pasted content becomes unchecked.
        if (
          value !== true &&
          value !== false
        ) {
          values[r][0] =
            false;
        }
      }

      range
        .setDataValidation(rule)
        .setValues(values);
    }
  );
}


function clearFilterSpacerCells_(
  sheet
) {
  [
    "B10",
    "B18",
    "B25",
    "B27"
  ].forEach(
    function(a1) {
      sheet
        .getRange(a1)
        .clearContent();
    }
  );
}


// ------------------------------------------------------------
// POWER DROPDOWN
// ------------------------------------------------------------

function powerDropdownRuleIsCorrect_(
  rule
) {
  if (!rule) {
    return false;
  }

  if (
    rule.getCriteriaType()
    !== SpreadsheetApp
      .DataValidationCriteria
      .VALUE_IN_LIST
  ) {
    return false;
  }

  const args =
    rule.getCriteriaValues();

  const actualValues =
    (
      args.length > 0
      && Array.isArray(args[0])
    )
      ? args[0].map(
          function(value) {
            return String(value);
          }
        )
      : [];

  const showDropdown =
    (
      args.length < 2
      || args[1] !== false
    );

  const sameValues =
    actualValues.length
    === HF_POWERS.length
    &&
    actualValues.every(
      function(value, index) {
        return (
          value
          === HF_POWERS[index]
        );
      }
    );

  return (
    sameValues
    && showDropdown
    && rule.getAllowInvalid()
       === false
  );
}


function repairPowerDropdown_(
  sheet
) {
  const cell =
    sheet.getRange("B20");

  const raw =
    String(
      cell.getValue()
      || ""
    ).trim();

  // Content protection only.
  if (raw) {
    const canonical =
      HF_POWERS.find(
        function(power) {
          return (
            power.toLowerCase()
            === raw.toLowerCase()
          );
        }
      );

    if (canonical) {
      if (canonical !== raw) {
        cell.setValue(
          canonical
        );
      }
    } else {
      cell.clearContent();
    }
  }

  // Preserve an already-correct dropdown rule completely.
  // This is deliberate: visual customization of the dropdown
  // remains the user's/template's responsibility.
  const existingRule =
    cell.getDataValidation();

  if (
    powerDropdownRuleIsCorrect_(
      existingRule
    )
  ) {
    return;
  }

  // Only rebuild when the functional rule is actually missing/wrong.
  const rule =
    SpreadsheetApp
      .newDataValidation()
      .requireValueInList(
        HF_POWERS,
        true
      )
      .setAllowInvalid(false)
      .build();

  cell.setDataValidation(
    rule
  );
}


// ------------------------------------------------------------
// STATUS
// ------------------------------------------------------------

function repairStatusValue_(
  sheet
) {
  const cell =
    sheet.getRange("B28");

  const value =
    String(
      cell.getValue()
      || ""
    )
      .trim()
      .toUpperCase();

  const allowed = [
    "",
    "RUNNING",
    "COMPLETED",
    "ERROR"
  ];

  if (
    !allowed.includes(value)
  ) {
    cell.clearContent();
    return;
  }

  if (value) {
    cell.setValue(value);
  }
}


// ------------------------------------------------------------
// SYSTEMS / TOTAL
// ------------------------------------------------------------

function restoreSystemsHeaders_(
  sheet
) {
  sheet
    .getRange("C1")
    .setValue("Systems");

  updateSystemsCounter_(
    sheet
  );
}


function updateSystemsCounter_(
  sheet
) {
  const lastRow =
    Math.max(
      sheet.getLastRow(),
      2
    );

  const values =
    sheet
      .getRange(
        2,
        3,
        lastRow - 1,
        1
      )
      .getDisplayValues()
      .flat();

  const unique =
    new Set();

  values.forEach(
    function(value) {
      const cleaned =
        String(
          value || ""
        ).trim();

      if (cleaned) {
        unique.add(
          cleaned.toLowerCase()
        );
      }
    }
  );

  sheet
    .getRange("D1")
    .setValue(
      "Total: "
      + unique.size
    );
}


// ------------------------------------------------------------
// RESULT HEADERS
// ------------------------------------------------------------

function restoreResultHeaders_(
  sheet
) {
  sheet
    .getRange("E1:M1")
    .setValues([[
      "System",
      "Status",
      "Body",
      "Ring",
      "Ring Type",
      "Reserve Level",
      "LS Distance",
      "Material",
      "Hotspot Count"
    ]]);

  // N = visual separator
  sheet
    .getRange("N1")
    .clearContent();

  sheet
    .getRange("O1:U1")
    .setValues([[
      "System",
      "Status",
      "Body",
      "Planet Type",
      "Landable",
      "Volcanism",
      "LS Distance"
    ]]);
}


// ------------------------------------------------------------
// PASTE-ONLY FORMAT PROTECTION
// ------------------------------------------------------------

function isLikelyMultiCellPaste_(
  e
) {
  if (!e || !e.range) {
    return false;
  }

  return (
    e.range.getNumRows() > 1 ||
    e.range.getNumColumns() > 1
  );
}


function repairProtectedPasteFormatting_(
  sheet,
  pastedRange
) {
  const style =
    SpreadsheetApp
      .getActiveSpreadsheet()
      .getSheetByName(
        HF_STYLE_SHEET
      );

  // No saved style template:
  // keep structure protection, but do not invent a format.
  if (!style) {
    return;
  }

  // A1:B28 protected filter/control panel.
  copyExactProtectedFormat_(
    style,
    sheet,
    pastedRange,
    1, 1,
    28, 2,
    1, 4
  );

  // C1:D1 protected Systems / Total header.
  copyExactProtectedFormat_(
    style,
    sheet,
    pastedRange,
    1, 3,
    1, 4,
    1, 7
  );

  // E1:U1 protected result headers + separator.
  copyExactProtectedFormat_(
    style,
    sheet,
    pastedRange,
    1, 5,
    1, 21,
    1, 10
  );
}


function copyExactProtectedFormat_(
  style,
  sheet,
  editedRange,
  targetRow1,
  targetCol1,
  targetRow2,
  targetCol2,
  sourceRow1,
  sourceCol1
) {
  const hit =
    intersection_(
      editedRange,
      targetRow1,
      targetCol1,
      targetRow2,
      targetCol2
    );

  if (!hit) {
    return;
  }

  const rows =
    hit.row2
    - hit.row1
    + 1;

  const cols =
    hit.col2
    - hit.col1
    + 1;

  const sourceStartRow =
    sourceRow1
    + (
      hit.row1
      - targetRow1
    );

  const sourceStartCol =
    sourceCol1
    + (
      hit.col1
      - targetCol1
    );

  style
    .getRange(
      sourceStartRow,
      sourceStartCol,
      rows,
      cols
    )
    .copyFormatToRange(
      sheet.getSheetId(),
      hit.col1,
      hit.col2,
      hit.row1,
      hit.row2
    );
}


// ------------------------------------------------------------
// HELPERS
// ------------------------------------------------------------

function getHotspotsSheet_() {
  return SpreadsheetApp
    .getActiveSpreadsheet()
    .getSheetByName(
      HF_SHEET_NAME
    );
}


function intersects_(
  range,
  row1,
  col1,
  row2,
  col2
) {
  return !(
    range.getLastRow() < row1 ||
    range.getRow() > row2 ||
    range.getLastColumn() < col1 ||
    range.getColumn() > col2
  );
}


function intersectsAny_(
  range,
  areas
) {
  return areas.some(
    function(area) {
      return intersects_(
        range,
        area[0],
        area[1],
        area[2],
        area[3]
      );
    }
  );
}


function intersection_(
  range,
  row1,
  col1,
  row2,
  col2
) {
  const r1 =
    Math.max(
      range.getRow(),
      row1
    );

  const c1 =
    Math.max(
      range.getColumn(),
      col1
    );

  const r2 =
    Math.min(
      range.getLastRow(),
      row2
    );

  const c2 =
    Math.min(
      range.getLastColumn(),
      col2
    );

  if (
    r1 > r2 ||
    c1 > c2
  ) {
    return null;
  }

  return {
    row1: r1,
    col1: c1,
    row2: r2,
    col2: c2
  };
}
