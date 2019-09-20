// exported typescript definitions for use in other files
import { Service } from '@opentrons/discovery-client'

// Redux action
// app/src/types.js
export type Action =
  | { type: 'shell:DOWNLOAD_LOGS'; payload: { logUrls: string[] } }
  | { type: 'shell:CHECK_UPDATE'; meta: { shell: true } }
  | { type: 'shell:DOWNLOAD_UPDATE'; meta: { shell: true } }
  | { type: 'shell:APPLY_UPDATE'; meta: { shell: true } }
  | {
      type: 'shell:CHECK_UPDATE_RESULT'
      payload: { available?: boolean; info?: UpdateInfo; error?: PlainError }
    }
  | { type: 'shell:DOWNLOAD_UPDATE_RESULT'; payload: { error?: PlainError } }
  | { type: 'buildroot:DOWNLOAD_PROGRESS'; payload: number }
  | { type: 'buildroot:DOWNLOAD_ERROR'; payload: string }
  | { type: 'buildroot:UPDATE_VERSION'; payload: string }
  | { type: 'buildroot:UPDATE_INFO'; payload: BuildrootUpdateInfo }
  | {
      type: 'buildroot:START_PREMIGRATION'
      payload: RobotHost
      meta: { shell: true }
    }
  | { type: 'buildroot:PREMIGRATION_DONE'; payload: string }
  | { type: 'buildroot:PREMIGRATION_ERROR'; payload: { message: string } }
  | {
      type: 'buildroot:READ_USER_FILE'
      payload: { systemFile: string }
      meta: { shell: true }
    }
  | { type: 'buildroot:USER_FILE_INFO'; payload: BuildrootUserFileInfo }
  | {
      type: 'buildroot:UPLOAD_FILE'
      payload: { host: RobotHost; path: string; systemFile: string | null }
      meta: { shell: true }
    }
  | { type: 'buildroot:FILE_UPLOAD_DONE'; payload: string }
  | { type: 'buildroot:UNEXPECTED_ERROR'; payload: { message: string } }
  | {
      type: 'discovery:START'
      payload: { timeout: number | null }
      meta: { shell: true }
    }
  | { type: 'discovery:FINISH'; meta: { shell: true } }
  | {
      type: 'discovery:REMOVE'
      payload: { robotName: string }
      meta: { shell: true }
    }
  | { type: 'discovery:UPDATE_LIST'; payload: { robots: Service[] } }
  | {
      type: 'config:UPDATE'
      payload: { path: string; value: unknown }
      meta: { shell: true }
    }
  | { type: 'config:SET'; payload: { path: string; value: unknown } }

// object representing an error
// app/src/types.js
export interface PlainError {
  name: string
  message: string
}

// app self-update info
// app/src/shell/update.js
export interface UpdateInfo {
  version: string
  files: Array<{ sha512: string; url: string }>
  releaseDate: string
  releaseNotes?: string
}

// robot host
// app/src/robot-api/types.js
export interface RobotHost {
  name: string
  ip: string
  port: number
}

// info for user-uploaded buildroot update
// app/src/shell/buildroot/types.js
export type BuildrootUserFileInfo = {
  systemFile: string
  version: string
}

// info for a auto-downloaded buildroot update
// app/src/shell/buildroot/types.js
export interface BuildrootUpdateInfo {
  releaseNotes: string
}

// log levels
// app/src/logger.js
export type LogLevel =
  | 'error'
  | 'warn'
  | 'info'
  | 'http'
  | 'verbose'
  | 'debug'
  | 'silly'

export type UrlProtocol = 'file:' | 'http:'

export type UpdateChannel = 'latest' | 'beta' | 'alpha'

export type DiscoveryCandidates = string | string[]

export type DevInternalFlag =
  | 'allPipetteConfig'
  | 'tempdeckControls'
  | 'enablePipettePlus'

export interface Config {
  devtools: boolean

  // app update config
  update: {
    channel: UpdateChannel
  }

  // robot update config
  buildroot: {
    manifestUrl: string
  }

  // logging config
  log: {
    level: {
      file: LogLevel
      console: LogLevel
    }
  }

  // ui and browser config
  ui: {
    width: number
    height: number
    url: {
      protocol: UrlProtocol
      path: string
    }
    webPreferences: {
      webSecurity: boolean
    }
  }

  analytics: {
    appId: string
    optedIn: boolean
    seenOptIn: boolean
  }

  // deprecated; remove with first migration
  p10WarningSeen: {
    [id: string]: boolean | null | undefined
  }

  support: {
    userId: string
    createdAt: number
    name: string
    email: string | null | undefined
  }

  discovery: {
    candidates: DiscoveryCandidates
  }

  // internal development flags
  devInternal?: {
    [F in DevInternalFlag]?: boolean
  }
}
