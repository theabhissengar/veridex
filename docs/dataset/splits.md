# Splits

`dataset/development/splits.json` maps `case_id` to `train` or `validation`.

`dataset/evaluation/` is held out.

A source video's frames, clips, and crops stay with that case. The checker in `veridex.domain.splits` rejects a derivative placed in another split or tier.
