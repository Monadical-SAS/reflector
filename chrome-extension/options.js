const api = document.getElementById('api')
const button = document.querySelector('button')

chrome.storage.local.get('key', ({ key }) => {
  if(key) api.value = key
})

button.addEventListener('click', () => {
  const key = api.value
  chrome.storage.local.set({ key }, () => {
    alert('Reflector API key set')
  })
})
