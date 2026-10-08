# Final checklist (every file, before upload)

## All documents
- [ ] Latest version, confirmed by checksum against the file the PI last approved
- [ ] Page count within limit; content that must not count (references, etc.) placed where the funder expects
- [ ] Fonts allowed and at or above minimum size everywhere, including tables, figure labels, headers, and footers; captions at or above the funder's caption rule, if it has one (`scripts/docx_audit.py --min-pt <body> --caption-min-pt <captions> --table-min-pt <tables>`, values from the requirements file)
- [ ] Margins, line spacing, character spacing, and page size compliant
- [ ] Track Changes switched off; all revisions accepted or rejected; all comments deleted
- [ ] No placeholders (`[CLARIFY]`, `TODO`, `XXX`, `XX%`, `(CITE …)`, `(REF)`, lorem ipsum, keyboard-mash filler, `⟦CONFIRM⟧`, highlighted text, "insert here")
- [ ] Fields updated in Word before export (caption numbers, cross-references, reference-manager bibliography)
- [ ] For an uploaded .docx: no unwanted hidden content (reference-manager abstracts, hidden text)
- [ ] Document properties cleaned (title, author, company, template leftovers)
- [ ] Every number, name, title, and date matches the numbers registry
- [ ] Required headings and sections present, in the required order
- [ ] Hyperlinks allowed or removed, per the rules
- [ ] PDF exported where the document's fonts are installed; fonts embedded (`pdffonts`); copied text is readable (ligatures and symbols)
- [ ] File named as the funder or the PI requires

## Project description / research strategy
- [ ] Every prompt in the call answered
- [ ] Reference list uploaded where the funder wants it (separate document if required) and not counted in the page limit
- [ ] Every citation in the reference list and vice versa (`scripts/cite_check.py --refs`); reference format as required
- [ ] Figure and table numbering continuous, every cross-reference correct (`scripts/figure_audit.py`)
- [ ] Figures legible at print size, checked at 100% in the PDF (especially any a past reviewer called hard to read); captions match the text
- [ ] No leftovers from cut scope (timeline rows, figure labels, risks, collaborators)
- [ ] Every promise in the vision and summary delivered by an activity, timeline row, budget line, and assessment
- [ ] Partner claims backed by letters

## Budget and justification
- [ ] Budget is in the template that will be submitted (funder's, institution's, or the system's own form); only input cells changed, formulas and structure intact
- [ ] Totals recomputed; year and overall caps respected; indirect rate and base correct
- [ ] Justification matches budget line by line, including section headers and summary tables (`scripts/budget_check.py --xlsx`)
- [ ] Justification matches the version of record if the sponsored-programs office has already entered the budget
- [ ] No activity in a year when the person doing it is off the budget
- [ ] Amount in the online form, letters, and summary matches the budget
- [ ] Workbook values stored (opened and saved in a spreadsheet app); correct sheet active; prints legibly; no hidden rows carrying amounts; highlight colors removed

## Letters
- [ ] Signed, on letterhead, dated with a plausible date; scanned PDFs checked visually
- [ ] One letter for every collaborator the narrative names, and no letter for anyone it no longer names
- [ ] Say what the call requires them to say
- [ ] Names, titles, and project title correct
- [ ] Merged per slot if the system takes one file

## Online form
- [ ] Every field drafted offline with a character count under the limit
- [ ] Contacts, institutional identifiers, and amounts verified
- [ ] Questions about other components (video, prior support) answered correctly

## Items outside the folder
- [ ] Each item that lives only in the submission system or a profile tool confirmed complete and certified (biosketch, current and pending support, collaborators list, data-plan web form, cover-sheet boxes and certifications)
- [ ] Institutional or departmental letter received if required

## Submission
- [ ] Final files in `04_final_submission/`, in upload order, with a README
- [ ] Uploads and form staged; the PI reviews and presses submit
- [ ] Confirmation and the funder-assembled PDF saved; submission recorded in the notes
- [ ] Archive cleaned up; lessons-learned note written
