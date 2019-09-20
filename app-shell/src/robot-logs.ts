// download robot logs manager
import { BrowserWindow } from 'electron'
import { Action, Dispatch } from './types'

export function registerRobotLogs(
  dispatch: Dispatch,
  mainWindow: BrowserWindow | null
) {
  return function handleIncomingAction(action: Action) {
    if (action.type === 'shell:DOWNLOAD_LOGS') {
      const {
        payload: { logUrls },
      } = action

      logUrls.forEach(url => {
        mainWindow && mainWindow.webContents.downloadURL(url)
      })
    }
  }
}
