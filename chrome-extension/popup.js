// showLatestTranscript()

document.getElementById('start').addEventListener('click', async () => {
    const tab = await getCurrentTab()
    if(!tab) return alert('Require an active tab')
    chrome.tabs.sendMessage(tab.id, { message: 'start' })
})

document.getElementById('stop').addEventListener('click', async () => {
    const tab = await getCurrentTab()
    if(!tab) return alert('Require an active tab')
    chrome.tabs.sendMessage(tab.id, { message: 'stop' })
})

// document.getElementById('clear').addEventListener('click', async () => {
//     chrome.storage.local.remove(['transcript'])
//     document.getElementById('transcript').innerHTML = ''
// })

// document.getElementById('options').addEventListener('click', async () => {
//     chrome.runtime.openOptionsPage()
// })

// chrome.runtime.onMessage.addListener(({ message }) => {
//     if(message == 'transcriptavailable') {
//         showLatestTranscript()
//     }
// })

// function showLatestTranscript() {
//     chrome.storage.local.get("transcript", ({ transcript }) => {
//         document.getElementById('transcript').innerHTML = transcript
//     })
// }

async function getCurrentTab() {
    const queryOptions = { active: true, lastFocusedWindow: true }
    const [tab] = await chrome.tabs.query(queryOptions)
    return tab
}
