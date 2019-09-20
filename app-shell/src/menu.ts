// application menu
import { Menu, MenuItemConstructorOptions } from 'electron'
import contextMenu from 'electron-context-menu'

import pkg from '../package.json'

// file or application menu
const firstMenu: MenuItemConstructorOptions = {
  role: process.platform === 'darwin' ? 'appMenu' : 'fileMenu',
}

const editMenu: MenuItemConstructorOptions = { role: 'editMenu' }

const viewMenu: MenuItemConstructorOptions = { role: 'viewMenu' }

const windowMenu: MenuItemConstructorOptions = { role: 'windowMenu' }

const helpMenu: MenuItemConstructorOptions = {
  role: 'help',
  submenu: [
    {
      label: 'Learn More',
      click: () => {
        require('electron').shell.openExternal('https://opentrons.com/')
      },
    },
    {
      label: 'Report an Issue',
      click: () => {
        require('electron').shell.openExternal(pkg.bugs.url)
      },
    },
  ],
}

const template = [firstMenu, editMenu, viewMenu, windowMenu, helpMenu]

export default function initializeMenu(devMode: boolean): void {
  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
  contextMenu({ showInspectElement: devMode })
}
