import { useContext } from 'react'

import { ActivityContext } from './activityContextState'


export function useActivity() {
  const context =
    useContext(ActivityContext)

  if (!context) {
    throw new Error(
      'useActivity must be used inside ActivityProvider.',
    )
  }

  return context
}
