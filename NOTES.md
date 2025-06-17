frontend explicitly calls backend to create meeting. upsert semantic (meeting gets "stale" somehow - how?)
frontend only listens for users own "leave" event to redirect away
how do we know it starts recording? meeting has different meeting configurations. to simplify, probably show the consent ALWAYS
Q: how S3 and SQS gets filled? by what system?


we have meeting entity, we have users. let's always ask users for consent in an overlay and send this to server to attach to the meeting entity, if we have it

- consent endpoint