// electron main entry point
import { app, dialog, ipcMain, BrowserWindow } from 'electron'

import createUi from './ui'
import initializeMenu from './menu'
import createLogger, { Logger } from './log'
import { getConfig, getStore, getOverrides, registerConfig } from './config'
import { registerDiscovery } from './discovery'
import { registerRobotLogs } from './robot-logs'
import { registerUpdate } from './update'
import { registerBuildrootUpdate } from './buildroot'
import { Dispatch } from './types'

const config = getConfig()
const log = createLogger(__filename)

log.debug('App config', {
  config,
  store: getStore(),
  overrides: getOverrides(),
})

const devMode = config.devtools

if (devMode) {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  require('electron-debug')({ isEnabled: true, showDevTools: true })
}

// hold on to references so they don't get garbage collected
let mainWindow: BrowserWindow | null = null
let rendererLogger

app.once('ready', startUp)
app.once('window-all-closed', () => app.quit())

function startUp(): void {
  log.info('Starting App')
  process.on('uncaughtException', error => log.error('Uncaught: ', { error }))

  mainWindow = createUi().once('closed', () => (mainWindow = null))

  rendererLogger = createRendererLogger()

  initializeMenu(devMode)

  // wire modules to UI dispatches
  const dispatch: Dispatch = action => {
    log.silly('Sending action via IPC to renderer', { action })
    mainWindow && mainWindow.webContents.send('dispatch', action)
  }

  const configHandler = registerConfig(dispatch)
  const discoveryHandler = registerDiscovery(dispatch)
  const robotLogsHandler = registerRobotLogs(dispatch, mainWindow)
  const updateHandler = registerUpdate(dispatch)
  const buildrootUpdateHandler = registerBuildrootUpdate(dispatch)

  ipcMain.on('dispatch', (_, action) => {
    log.debug('Received action via IPC from renderer', { action })
    configHandler(action)
    discoveryHandler(action)
    robotLogsHandler(action)
    updateHandler(action)
    buildrootUpdateHandler(action)
  })

  if (config.devtools) {
    installAndOpenExtensions().catch(error =>
      dialog.showErrorBox('Error opening dev tools', error)
    )
  }

  log.silly('Global references', { mainWindow, rendererLogger })
}

function createRendererLogger(): Logger {
  log.info('Creating renderer logger')

  const logger = createLogger()
  ipcMain.on('log', (_, info) => logger.log(info))

  return logger
}

function installAndOpenExtensions(): Promise<unknown> {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const devtools = require('electron-devtools-installer')
  const forceDownload = !!process.env.UPGRADE_EXTENSIONS
  const install = devtools.default
  const extensions = ['REACT_DEVELOPER_TOOLS', 'REDUX_DEVTOOLS']

  return Promise.all(
    extensions.map(name => install(devtools[name], forceDownload))
  )
}
