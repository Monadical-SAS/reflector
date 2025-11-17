# Source: https://docs.daily.co/reference/rest-api/rooms/callTransfer

# sipCallTransfer

Daily.co provides two methods for handling call transfers: `sipCallTransfer` and `sipRefer`. Both methods maintain the original SIP/PSTN connection, meaning the initial caller's connection does not disconnect during the transfer. However, they serve different purposes and have distinct implementations.

## Key Differences

### sipCallTransfer

Best for internal transfers within your Daily-powered infrastructure

  * Keeps the call existing sip connection attachment with Daily while connecting a secondary sip connection. This is most commonly ideal for transferring calls between Daily Rooms. If there is an existing connection from "sip:[someone@sip.elsewhere.com](mailto:someone@sip.elsewhere.com)" and you want to move the call from "[dailyroom-1@domain.sip.daily.co](mailto:dailyroom-1@domain.sip.daily.co)" to "[dailyroom-2@domain.sip.daily.co](mailto:dailyroom-2@domain.sip.daily.co)" then use `sipCallTransfer`.
  * Calls can also be forwarded to an external sip address, i.e., non-Daily SIP addresses, however, the Daily SIP connection will remain active and Daily continues to manage and route the connection. In this example, the existing connection from "sip:[someone@sip.elsewhere.com](mailto:someone@sip.elsewhere.com)" to "[dailyroom-1@domain.sip.daily.co](mailto:dailyroom-1@domain.sip.daily.co)" needs to be forwarded to "[someother@sip.anotherplace.com](mailto:someother@sip.anotherplace.com)" then you can also use `sipCallTransfer`.



### sipRefer

Suitable when calls come from external sip addresses and need to transfered back to that external phone systems, call centers, or SIP providers. In this case you want to avoid the latency loop from the external system to daily and back.

  * Enables transfers to external SIP endpoints, however, both the originating and terminating SIP addresses MUST be outside Daily's SIP network
  * Removes Daily from the connection path after transfer and provide direct endpoint-to-endpoint connection after transfer.



## Use Case Considerations

Choose `sipCallTransfer` when:

  * Transferring calls between Daily Rooms
  * Maintaining Daily's features and capabilities is important
  * You want to keep analytics and monitoring within Daily's ecosystem



Choose `sipRefer` when:

  * The origination address is outside Daily's SIP network and transferring to external SIP endpoints
  * Minimizing intermediary connections is a priority



## Implementation Options

You can implement these transfers through:

  1. REST API endpoints:

     * [SIP Call Transfer](/reference/rest-api/rooms/callTransfer/sip-call-transfer)
     * [SIP Refer](/reference/rest-api/rooms/callTransfer/sip-refer)
  2. Client SDK methods :

     * `sipCallTransfer()`: [daily-js](/reference/daily-js/instance-methods/sip-call-transfer), [daily-python](https://reference-python.daily.co/api_reference.html#daily.CallClient.sip_call_transfer)
     * `sipRefer()`: [daily-js](/reference/daily-js/instance-methods/sip-refer), [daily-python](https://reference-python.daily.co/api_reference.html#daily.CallClient.sip_refer)



## Pricing Considerations

The choice between `sipCallTransfer` and `sipRefer` may have pricing implications based on your usage patterns and requirements. For detailed pricing information and guidance on which method best suits your needs, please contact:

  * Email: [help@daily.co](mailto:help@daily.co)
  * Sales team: Contact for enterprise pricing and volume discussions


