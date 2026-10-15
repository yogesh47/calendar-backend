# TPO event flow — TPO kya karta hai, aur kya hota hai

Ye poora flow BRD se hai. Har kadam par do baatein likhi hain — **TPO ko kya
dikhta hai**, aur **hamare DB me kya hota hai**.

---

## TPO kar kya sakta hai

| Kaam | Kis event par |
|---|---|
| Event banana | har type ka |
| Event edit karna | **sirf wahi jo usne khud banaya** |
| Event cancel karna | **sirf wahi jo usne khud banaya**, aur wo bhi end time se pehle |
| Apna reminder banana | private — kisi aur ko nahi dikhta |
| Baaki TPO ke event dekhna | dekh sakta hai, badal nahi sakta |

College ke saare TPO ek hi calendar dekhte hain. Par button sirf banane wale ko
milte hain. Doosre TPO ko ye line dikhti hai:

> View only. Only Ravi Sharma can edit or cancel this event.

---

## 1. Event banana

### TPO ko kya dikhta hai

Ek hi drawer right side se khulta hai. **Event Type** chunte hi baaki form badal
jaata hai:

| Type chuna | Form me kya aata hai |
|---|---|
| PPT, Company Visit, Training, Orientation, Practice Test, Other | Start Time, End Time, Mode, Venue ya Platform — sab zaroori |
| Online Assessment | Start Time, End Time (test ki window). Mode aur Venue **nahi** poochhte |
| Deadline | sirf Date. Time, Mode, Venue kuch nahi — "All-day item" likha aata hai |
| My Reminder | Date, time marzi, note. Audience nahi poochhte |

```
Event Type *   [ Pre-Placement Talk ▾ ]
Event Title *  [ Deloitte Pre-Placement Talk ]      max 120
Company        [ Deloitte ▾ ]                       optional
Date *         [ 2 Oct 25 ]                         aaj ya aage ka
Start Time *   [ 10:00 AM ]
End Time *     [ 12:00 PM ]                         start ke baad hona chahiye
Mode *         (•) Offline   ( ) Online
Venue *        [ Auditorium A ]                     max 200
Description    [ ... ]                              optional, max 1000
```

Company chunte hi ek hint aati hai — "Existing Deloitte events: Online
Assessment — 2 Oct (Ravi Sharma)". Ye sirf batane ke liye hai, rokti nahi.

### Audience chunna

Char kadam, upar se neeche:

```
Opportunity Type   (•) Job   ( ) Internship   ( ) General
Course             [x] BTech  [ ] MBA  [ ] MCA
Batch              [x] 2027 (Final year)
Department         [x] CSE   [x] IT   [ ] All departments
```

| Opportunity Type | Kaun se batch chun sakte hain |
|---|---|
| Job | sirf final year wala batch |
| Internship | pre-final aur final year |
| General | koi bhi batch |

Jaise hi kuch badalta hai, neeche ka number update hota hai:

> **120 students will be notified**

Agar koi student match na kare to likha aata hai "0 students match this
audience." aur **Publish button band ho jaata hai**.

TPO kisi ek student ko haath se jod ya hata nahi sakta. Sirf ye char level
chunta hai.

### Publish dabane par

1. Event calendar par **turant** dikh jaata hai, neele rang me
2. Jo students audience me aate hain unhe bell, push aur email jaata hai —
   "New event: Deloitte Pre-Placement Talk on 2 Oct, 10:00 AM. Check your Campus Calendar."
3. TPO ko message dikhta hai — "Event published. 120 students notified."

### DB me kya hota hai

| Table | Kya banta hai |
|---|---|
| `calendar_event` | ek row — type, title, date, time, mode, venue, `created_by` me TPO ki id |
| `calendar_event_audience` | ek row — opportunity type, courses, batches, departments |
| `calendar_event_recipient` | **har student ki ek row**, `state = active` |
| `calendar_nudge` | har student ke liye reminder ka time — 1 din pehle aur 1 ghanta pehle |

> Student list yahin **freeze** ho jaati hai. Kal koi naya student us course aur
> batch me aaye to use ye event nahi milega — kyunki uski row bani hi nahi.

---

## 2. Calendar par kaisa dikhta hai

```
            Mon 1    Tue 2         Wed 3                Thu 4
          ┌────────────────────────────────────────────────────┐
 all-day  │                 │ Submit documents to TPO office │  │
          ├────────────────────────────────────────────────────┤
  9 AM    │                                                    │
 10 AM    │         ┌──────────────┐                           │
 11 AM    │         │ Deloitte PPT │                           │
 12 PM    │         └──────────────┘                           │
```

| Kya | Kahan dikhta hai |
|---|---|
| Jiske paas time hai (PPT, visit, training…) | grid me, start se end tak ka box |
| Deadline | sabse upar wali patti me — uska time hota hi nahi |

Poore din ka event alag se chunne ka option **nahi** hai. Poora din hai to TPO
9:00 AM – 5:00 PM bhar deta hai, aur grid me lamba box ban jaata hai.

---

## 3. Event edit karna

### Kaun aur kab

Sirf banane wala TPO. Aur sirf tab tak jab tak event ka end time nahi nikal
jaata.

**Event Type kabhi nahi badal sakta.** Baaki sab badal sakta hai.

### Do tarah ke badlav

| Kis cheez ka badlav | Students ko notification |
|---|---|
| Date, Start Time, End Time, Mode, Venue ya Platform, Audience | **hamesha jaata hai** |
| Title, Description, Company | ek checkbox aata hai — "Notify students about this change". TPO tick kare tabhi jaata hai |

### Audience badalne par

Save se pehle ek summary dikhti hai, taaki TPO ko pata ho kis par kya asar padega:

```
Updated   BTech · 2027 · CSE        85 students
Added     BTech · 2027 · IT         35 students
Removed   MBA · 2027 · Marketing    12 students

Reason for change  [ Venue change ho gaya tha ]        optional
```

Teeno group ko alag-alag message jaata hai:

| Kisko | Message |
|---|---|
| Jo rahe | "[Title] has been updated: [kya badla]." |
| Jo naye jude | "New event: [Title] on [Date], [Time]." |
| Jo hata diye gaye | "[Title] on [Date] no longer applies to you. [Reason]" |

Save button ka naam bhi badalta hai — notification jaayegi to "Save & Notify
120", warna sirf "Save Changes".

### DB me kya hota hai

| Table | Kya hota hai |
|---|---|
| `calendar_event` | row update, `updated_at` apne aap badal jaata hai |
| `calendar_event_audience` | row update |
| `calendar_event_recipient` | naye students ki **nayi row**, hataye gaye students ki row ka `state = removed` aur `removed_reason` me wajah |
| `calendar_nudge` | date badli to pending nudges naye date par shift |

> **Hataye gaye student ki row delete nahi hoti.** `state = removed` isliye
> rakhte hain taaki student ko uske calendar par dikhe ki "ab ye mujh par lagu
> nahi hota". Row hata dete to use kabhi pata hi nahi chalta.

---

## 4. Event cancel karna

### TPO ko kya dikhta hai

```
Cancel Event

Deloitte Pre-Placement Talk
2 Oct 2025 · 120 students will be notified

Reason *
( ) Postponed
( ) Company Withdrew
( ) Created by Mistake
( ) Other  →  [ short explanation, max 200 ]
```

Postponed chunne par ek tip aati hai — "You can edit the date instead of
cancelling." TPO phir bhi cancel kar sakta hai.

### Cancel ke baad

| Reason | Kya hota hai |
|---|---|
| Postponed, Company Withdrew, Other | Event calendar par **rehta hai** — halka, kaata hua, "Cancelled" badge ke saath. Students ko jaata hai: "[Title] on [Date] has been cancelled. Reason: [Reason]." |
| **Created by Mistake** | Event students ke calendar se **hat jaata hai**. Unhe jaata hai: "Please ignore the earlier notification about [Title]." TPO ko wo abhi bhi Cancelled ki tarah dikhta hai |

Teen pakki baatein:
- Cancel ki hui event **wapas nahi aa sakti** — dobara chahiye to nayi banani padegi
- Row kabhi **delete nahi hoti** — record ke liye rakhte hain
- Event ke sabhi pending reminder **cancel ho jaate hain**

### DB me kya hota hai

| Table | Kya hota hai |
|---|---|
| `calendar_event` | `status = cancelled`, `cancel_reason`, `cancel_note`, `cancelled_by`, `cancelled_at` |
| `calendar_event_recipient` | sirf Created by Mistake par sab rows `state = removed` |
| `calendar_nudge` | pending nudges `status = cancelled` |

---

## 5. TPO ka apna reminder

Wahi drawer, Event Type me **My Reminder**.

```
Event Type *   [ My Reminder ▾ ]
Title *        [ Call Deloitte HR ]       max 120
Date *         [ 1 Oct 25 ]
Time           [ 11:00 AM ]               optional
Remind me      [ 1 hour before ▾ ]
Note           [ ... ]                    optional, max 500
```

Audience, mode, venue kuch nahi poochha jaata. Ye **sirf TPO ko** dikhta hai,
kisi student ko nahi, kisi doosre TPO ko bhi nahi.

Ise TPO edit bhi kar sakta hai aur **delete** bhi — event ki tarah cancel nahi
karna padta. Delete par ek confirmation aata hai: "Delete this reminder?"

DB me ye `calendar_reminder` table me jaata hai, `calendar_event` me nahi.

---

## 6. Jo TPO nahi kar sakta

| Cheez | Kyun |
|---|---|
| Doosre TPO ka event edit ya cancel | sirf banane wala kar sakta hai |
| Event Type badalna | publish ke baad lock ho jaata hai |
| Ek-ek student jodna ya hatana | audience sirf course, batch, department se banti hai |
| Section se target karna | BRD me section ka option hai hi nahi |
| Cancel ki hui event wapas lana | nayi banani padegi |
| Event permanently delete karna | record ke liye row rehti hai |
| Purana event edit karna | end time nikal gaya to edit band |
| Job ki application deadline banani ya hatani | wo apne aap jobs se aati hai |

---

## 7. Ek nazar me — poora rasta

```
TPO drawer kholta hai
        ↓
type chunta hai  →  form uske hisaab se badalta hai
        ↓
audience chunta hai  →  "120 students will be notified"
        ↓
Publish
        ↓
┌──────────────────────────────────────────────┐
│ calendar_event           1 row               │
│ calendar_event_audience  1 row               │
│ calendar_event_recipient 120 rows (active)   │
│ calendar_nudge           reminders schedule  │
└──────────────────────────────────────────────┘
        ↓
students ko bell + push + email
        ↓
"Event published. 120 students notified."
```

---

## Source

| Kya | BRD me kahan |
|---|---|
| Event banana, fields, live count | Create Event |
| Kis type par kya poochha jaata hai | Event Types |
| Audience ke char level | Target Audience |
| Edit ke niyam, important vs minor | Edit Event |
| Cancel ke reason aur asar | Cancel Event |
| TPO ka apna reminder | TPO My Reminder |
| Kis badlav par kaunsi notification | Event Notifications |
