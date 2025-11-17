# Source: https://docs.daily.co/reference/rest-api/dialin

# Dialin

When a SIP Interconnect call or a Pinless phone call arrives, it is placed on hold until the developer creates a room and the room is ready for the phone call to be patched in via the [pinlessCallUpdate](/reference/rest-api/dialin/pinless-call-update).

An example of this is implemented in the [pipecat voice bot](https://docs.pipecat.ai/telephony/daily-webrtc#configuring-your-pipecat-bot), when [`dialin-ready`](https://reference-python.daily.co/api_reference.html#daily.EventHandler.on_dialin_ready) fires, the `bot-runner.py` forwards the call on hold to the pipecat bot.
