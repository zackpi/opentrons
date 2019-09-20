// Type definitions for node-stream-zip
// Project: https://github.com/antelle/node-stream-zip
// Definitions by: Opentrons Labworks <https://github.com/Opentrons>

/// <reference types="node" />

declare module 'node-stream-zip' {
  export interface Options {
    file: string
    storeEntries?: boolean
    skipEntryNameValidation?: boolean
  }

  export interface Entry {
    verMade: number
    version: number
    flags: number
    method: number
    time: number
    crc: number
    compressedSize: number
    size: number
    fnameLen: number
    extraLen: number
    comLen: number
    diskStart: number
    inattr: number
    attr: number
    offset: number
    headerOffset: number
    name: string
    isDirectory: boolean
    comment: string | null
  }

  export interface StreamReadyCallback {
    (error: Error, stream: NodeJS.ReadableStream): unknown
  }

  export default class StreamZip extends NodeJS.EventEmitter {
    constructor(options: Options)
    entry(name: string): Entry | undefined
    entries(): { [name: string]: Entry }
    stream(entry: string | Entry, ready: StreamReadyCallback): void
    entryDataSync(entry: string | Entry): Buffer
    close(): void
  }
}
