# Job Hunter Agent

סוכן מקומי שאוסף משרות פיתון, דאטה ו-AI (בישראל ומרחוק), מדרג כל משרה מול קורות החיים שלכם, ומציג את התוצאות בדשבורד שבו עוקבים אחרי הגשת המועמדויות.

## מה הוא עושה

1. **אוסף** משרות מ-LinkedIn, Indeed ו-Google (דרך JobSpy), מדפי הקריירה של כ-40 חברות ישראליות, ומאתרי עבודה מרחוק.
2. **מסנן** לפי מיקום (ישראל, או מרחוק שפתוח לישראל), סוג תפקיד, ותק וגיל המשרה.
3. **מדרג** בשני שלבים: ציון ראשוני חינמי (TF-IDF וחפיפת כישורים), ואז הערכה של מודל שפה למשרות הטובות ביותר.
4. **שומר** ב-SQLite. הסטטוס וההערות שלכם לא נדרסים לעולם.
5. **מציג** בדשבורד Streamlit בעברית.

הסוכן עובד גם בלי מודל שפה (ציון ראשוני בלבד). מודל שפה משפר את הדירוג ומוסיף הסברים, כישורים חסרים וטיפ לקורות החיים.

## התקנה

דרישות: Python 3.11 ומעלה, Windows.

```powershell
pip install -r requirements.txt
```

1. שימו את קורות החיים (PDF, DOCX או TXT) בתיקייה `cv/`. הקובץ החדש ביותר נבחר אוטומטית.
2. אופציונלי, למודל שפה: העתיקו את `.env.example` לקובץ בשם `.env` ושימו בו `ANTHROPIC_API_KEY=...`. אל תכניסו מפתח לקובץ `.env.example`, כי הוא נכנס ל-git.
3. אם המפתח אינו משויך ל-workspace, ה-ID שלו נמצא ב-`config.yaml` תחת `llm.anthropic_workspace_id`.

בלי מפתח (או עם `llm.provider: none`) הכול עובד עם ציון ראשוני.

## שימוש

```powershell
python run_agent.py                  # ריצה מלאה: איסוף, סינון, דירוג, שמירה
python run_agent.py --no-llm         # ציון ראשוני בלבד (חינם)
python run_agent.py --sources ats,remotive --limit 50   # ריצה חלקית
python run_agent.py --dry-run        # בלי כתיבה למסד הנתונים, מציג את 15 המובילות
python run_agent.py --rescore        # דירוג מחדש מול קורות החיים הנוכחיים
python run_agent.py --check-companies   # בדיקת רשימת החברות
streamlit run dashboard.py           # הדשבורד
pytest -q                            # הבדיקות
```

ריצה מלאה אורכת כמה דקות. רוב הזמן הולך על JobSpy, שמחכה בין שאילתות כדי ש-LinkedIn לא יחסום.

## מצב ג'וניור ועיצוב

- **ללא דרישת ניסיון:** `filters.max_required_years` ב-`config.yaml` (ברירת מחדל 0) מסנן החוצה משרות שמציינות שנות ניסיון נדרשות. בדשבורד יש מתג באותו שם בסרגל הצד. כדי לראות הכול, כבו את המתג או הגדירו `null`.
- **מצב כהה:** מתג "מצב כהה" בתחתית סרגל הצד.

## הרצה יומית אוטומטית

```powershell
powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1            # כל יום ב-08:30
powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1 -At 7:15am
powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1 -RunNow    # רישום והפעלה חד-פעמית
powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1 -Remove    # הסרה
```

המשימה נקראת `JobHunterAgent` ונראית ב-Task Scheduler. אם המחשב היה כבוי בשעה המתוכננת, הריצה תתבצע כשיידלק. הלוגים נמצאים ב-`data/logs/`.

## התראה על התאמות חזקות

ב-`config.yaml`:

```yaml
notify:
  enabled: true
  min_score: 80
```

בסוף ריצה שמצאה משרות חדשות בציון 80 ומעלה תופיע התראה על שולחן העבודה.

## הגדרות

הכול ב-`config.yaml`: מילות חיפוש, מסננים, מספר המשרות שנשלחות למודל (`matching.llm_top_n`), והמודל עצמו (`llm.model`). חברות נוספות מוסיפים ב-`companies.yaml`. אם החילוץ מקורות החיים שגוי, אפשר לתקן אותו ב-`profile.overrides` בלי לערוך את הקובץ.

## מבנה הפרויקט

```
run_agent.py       הרצת הסוכן
dashboard.py       הדשבורד
config.yaml        הגדרות
companies.yaml     חברות לשליפה ישירה
jobhunter/         הלוגיקה: איסוף, סינון, דירוג, מסד נתונים, גרף LangGraph
ui/                שכבת העיצוב של הדשבורד (מבוססת על קובץ ה-Figma)
scripts/           בדיקת חברות, תזמון ל-Windows
tests/             בדיקות, כולל תשובות מוקלטות של האתרים
docs/              ארכיטקטורה ותוכנית מימוש
```

## פתרון תקלות

- **`401 invalid x-api-key`**: המפתח שגוי או נמחק. צרו מפתח חדש בקונסולה של Anthropic.
- **`credit balance is too low`**: צריך להוסיף יתרה ב-Plans & Billing.
- **`not scoped to a workspace`**: הגדירו `llm.anthropic_workspace_id`, או צרו מפתח בתוך workspace.
- **LinkedIn מחזיר 429**: LinkedIn חוסם בקשות מהירות. הריצה ממשיכה עם המקורות האחרים. אפשר להקטין את `search.results_per_query`.
- **Glassdoor "not available for ISRAEL"**: Glassdoor לא תומך בישראל. אפשר להסיר אותו מ-`sources.jobspy.sites`.
- **"another run is in progress"**: רצה ריצה אחרת. אם היא נתקעה, מחקו את `data/run.lock`.
- **הדשבורד לא מתעדכן אחרי שינוי עיצוב**: הפעילו מחדש את Streamlit, כי שינויי theme דורשים הפעלה מחדש.

## מגבלות

- אין סורקים ישירים ל-AllJobs ו-Drushim. משרות מהם מגיעות רק אם Google Jobs מציג אותן.
- חברות שמשתמשות ב-Comeet מגיעות דרך JobSpy בלבד.
- סוכן התאמת קורות החיים למשרה (שלב 8 בתוכנית) עדיין לא נבנה.
