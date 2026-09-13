document.addEventListener('keydown', (event) => {
  if (
    event.key !== 'Enter'
    || event.defaultPrevented
    || event.isComposing
    || event.shiftKey
    || event.altKey
    || event.ctrlKey
    || event.metaKey
  ) {
    return
  }

  const target = event.target

  if (!(target instanceof HTMLInputElement)) {
    return
  }

  const form = target.form

  if (
    !form
    || !form.hasAttribute('data-submit-on-enter')
  ) {
    return
  }

  if (
    ['button', 'checkbox', 'file', 'radio', 'reset', 'submit']
      .includes(target.type)
  ) {
    return
  }

  event.preventDefault()
  form.requestSubmit()
})
