---
skill: complete-the-square
subject: math
---

# Quadratische Ergänzung

Die quadratische Ergänzung formt ein Polynom in ein vollständiges Quadrat plus
Restterm um. Sie ist die Grundlage der quadratischen Lösungsformel und hilft, eine
Gleichung der Form ax² + bx + c = 0 systematisch zu lösen.

Man halbiert den Koeffizienten von x, quadriert ihn und addiert sowie subtrahiert
diesen Wert, um ein Binom zu erzeugen. Verwandt: [[quadratic-formula]]. Wer hier
sicher ist, versteht auch, woher die Lösungsformel kommt.

```sql
-- frische Detailzahl bei Bedarf (Sidecar, NICHT mit-embeddet)
SELECT avg(mastery) FROM learner_state ls
JOIN skills s ON s.id = ls.skill_id
WHERE s.key = 'complete-the-square';
```
