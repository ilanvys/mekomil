# Trigger-Accuracy Eval Prompt for mekomIL

Paste everything under **The prompt** into Claude with browser control enabled
(Claude in Chrome, or Cowork connected to Claude in Chrome). Claude drives
claude.ai, runs every scenario in a fresh chat and judges the routing result.

This evaluation checks routing only: whether a skill loaded, which skill loaded
and whether the disclosure was honest. It does not grade the specialist
skill's factual content.

## Prerequisites

- A claude.ai account with the mekomIL connector or skill enabled.
- A Chrome tab already logged in to claude.ai.
- Record the model and effort level shown in the composer.
- Prefer a clean test account because memory and preferences can affect routing.

## The prompt

````text
You are running a trigger-accuracy QA pass for the mekomIL skill
router on claude.ai. Use the browser tools to drive the claude.ai web chat. Do
not answer the test questions yourself.

## What the router is supposed to do

It decides mid-conversation whether to load a specialist skill from the
skills-il catalog. It should load one only when all three hold:

1. The question is Israel- or Hebrew-specific in a way general knowledge
   handles badly.
2. A catalog entry matches the actual task, not just a shared keyword.
3. Loading the skill would change the answer rather than decorate it.

Router rules to check:

- Load at most two skills per turn.
- Load two only when the user explicitly asks for two distinct workstreams and
  no single skill covers both. Never load a second skill speculatively.
- Before applying a skill, state in one line which skill loaded and that it came
  from skills-il through mekomIL. The expected disclosure format is:
  `↯ טוען מיומנות: <skill-name> (skills-il, דרך mekomIL) — לשיחה הזו בלבד`
- Never present a value as retrieved unless a tool call returned it.
- Outside the disclosure line, do not expose internal wording such as "the
  skill says" or "לפי הסקיל" as if the user knows the mechanism.

## How to run each case

For every row in the test set:

1. Navigate to `https://claude.ai/new`. Use one fresh chat per case and never
   reuse a chat.
2. Insert the prompt with JavaScript, not simulated typing. Hebrew typed through
   the computer tool can silently lose spaces or punctuation:

   ```js
   const el = document.querySelector('[contenteditable="true"]');
   el.focus();
   document.execCommand('selectAll');
   document.execCommand('delete');
   document.execCommand('insertText', false, '<PROMPT>');
   await new Promise(r => setTimeout(r, 800));
   document.querySelector('button[aria-label="Send message"]').click();
   ```

   Read the sent message back and confirm it exactly matches the prompt. If it
   does not, discard the chat and retry.
3. Wait until the page says `Claude finished the response`. Skill loads and web
   searches can take 1–3 minutes. Poll roughly every 20 seconds; do not stop at
   `Claude is responding`.
4. Keep at most three responses running concurrently. If the site reports
   `Too many responses running at once`, wait for one to finish and retry.
5. Capture the chat URL, tool-activity summary, disclosure line, loaded skill
   names and reply text. Page text may repeat a tool row three times as a
   rendering artifact; do not treat those copies as separate calls.
6. Record the model and effort level once per run.

## How to judge each case

For each scenario record Fired (Y/N), the skill names and a verdict:

- `FIRE` + a fitting skill loaded: PASS.
- `FIRE` + no skill loaded: FAIL (false negative).
- `SILENT` + a skill loaded: FAIL (false positive).
- `SILENT` + no skill loaded: PASS.
- `EITHER`: PASS either way; explain the decision in one line.
- A keyword match that does not fit the actual task: FLAG as a wrong match.
- More than two skills: FAIL.
- Two skills without two explicit, distinct workstreams, or when one skill
  covers both: FAIL as speculative loading.

Also report whether the disclosure is present, accurate and matches the fixed
format. Check that the response separates skill material, web verification and
general knowledge. Recompute any arithmetic. Keep the verdict about routing;
record obvious factual problems as `content, out of scope`.

## Cross-case checks

After all scenarios, compare these related cases for contradictions:

- C03 vs R04: urban-renewal majority thresholds.
- M02 vs X02: the statutory cap on rental guarantees.
- M01 vs M07: advance shelter preparation versus choosing protection during an alert.
- R01 vs X01: aliyah benefits.

If a silent answer contradicts an answer that loaded a skill, report the silent
case as a likely false negative.

## Test set

| ID | Prompt | Expected | Notes |
|---|---|---|---|
| M01 | אין לי ממד, איך מכינים מקום מוגן בדירה? | EITHER | Official Home Front Command research is also acceptable. |
| M02 | מצאתי דירה, לפני שאני חותם על החוזה על מה להסתכל? | FIRE | Fair Rental Law and guarantee-cap specifics. |
| M03 | איפה מחפשים דירות בחיפה, יד2 או מדלן? | FIRE | The apartment-hunting skill can add local market context. |
| M04 | החנות לא מחזירה כסף על מוצר פגום, 900 שקל | FIRE | Check for a genuine consumer route, not a keyword-only match. |
| M05 | עיקרו לי את חשבון הבנק בגלל חוב לעירייה | FIRE | Municipal administrative collection versus Execution Office enforcement. |
| M06 | רואה החשבון מבקש הנהלת חשבונות מסודרת, מה זה אומר בפועל? | FIRE | Flag an automation skill if it does not fit the actual task. |
| M07 | באזעקה אני במקלט ציבורי או בחדר מדרגות? מה עדיף | FIRE | Current safety instructions can materially change the answer. |
| C01 | משתכר 19,500 ברוטו ומפריש 6% לפנסיה. כמה נכנס לקרן בחודש? | EITHER | Recompute the arithmetic; either route may be reasonable. |
| C02 | 38 ימי מילואים, שכר 15 אלף. כמה תגמול מגיע? | FIRE | The 40% remainder rule makes 38 days equal 39.2 payable days: 19,600 ₪ at 500 ₪ per day. |
| C03 | 3 בעלי דירות מתוך 12 מסרבים לתמא. יש רוב לפרויקט? | FIRE | תמ״א is an explicit trigger; compare with R04. |
| C04 | כמה זה 12,000 שקל בדולר לפי השער היציג? | FIRE | The official representative rate is a live Israeli value. |
| C05 | נולד לנו ילד ראשון. מה גובה מענק הלידה? | EITHER | A current official web lookup is also acceptable. |
| C06 | משכנתה של 1.2 מיליון ל-25 שנה בריבית 5%. מה ההחזר החודשי? | SILENT | Pure calculation; expected payment is approximately 7,015 ₪. |
| R01 | עולה חדש - מה בדיוק בסל הקליטה ומתי כל תשלום נכנס? | FIRE | |
| R02 | אמא שלי בת 78 וצריכה סיעוד. אילו טפסים של ביטוח לאומי? | FIRE | |
| R03 | מה המסלולים המדויקים של המילגה לחיילים משוחררים? | FIRE | |
| R04 | תמא 38/2 מול פינוי בינוי - מה ההגנות שלי כבעל דירה בכל מסלול? | FIRE | |
| X01 | עולה חדש שפותח עסק עצמאי - מה צריך גם ברשות המס וגם במשרד הקליטה? | FIRE | Two skills are allowed if no single skill covers both explicit workstreams. |
| X02 | השתחררתי מהצבא ואני רוצה לשכור דירה ראשונה | EITHER | A fitting single skill or a clarifying question is acceptable. |
| X03 | העסק נפגע במלחמה - גם פיצוי וגם איך מעדכנים מקדמות מס הכנסה | FIRE | Two skills are expected because the prompt explicitly asks for two separate processes. |

## Report format

Start with model, effort level, date, case count and number of cases that fired.
Then provide:

| ID | Expected | Fired | Skill(s) | Disclosure OK | Verdict | One-line reason |
|---|---|---|---|---|---|---|

Order findings by severity: rule violations, false negatives, false positives
or wrong matches, disclosure drift, then content issues marked out of scope.
Finish with one chat URL per case so a human can audit the verdicts.

Do not change account settings, connectors or memory during the run. If a step
requires one of those changes, stop and report what is needed.
````

## Known browser-runner issues

- Simulated Hebrew typing can drop characters; insert text with JavaScript and
  verify the sent prompt.
- Pressing Enter may not submit after programmatic insertion; click the send
  button.
- Page text can repeat tool rows three times; this is a rendering artifact.
- Skill loads and web searches can take several minutes; wait for the explicit
  completion state.
- Claude.ai rejects a fourth concurrent response; retry after one of the first
  three finishes.
