import { EventEmitter } from 'events'

export interface Candidate {
  ip: string
  port: number
}

export interface Service {
  name: string
  ip: string | null
  port: number
  // IP address (if known) is a link-local address
  local: boolean | null
  // GET /health response.ok === true
  ok: boolean | null
  // GET /server/health response.ok === true
  serverOk: boolean | null
  // is advertising on MDNS
  advertising: boolean | null
  // last good /health response
  health: object | null
  // last good /server/health response
  serverHealth: object | null
}

export interface Options {
  pollInterval?: number
  services?: Service[]
  candidates?: Array<string | Candidate>
  nameFilter?: Array<string | RegExp>
  ipFilter?: Array<string | RegExp>
  portFilter?: number[]
  logger?: unknown
}

export const SERVICE_EVENT = 'service'
export const SERVICE_REMOVED_EVENT = 'serviceRemoved'

export class DiscoveryClient extends EventEmitter {
  services: Service[]
  candidates: Candidate[]

  constructor(options: Partial<Options>)
  start(): this
  stop(): this
  add(ip: string, port?: number): this
  remove(name: string): this
  setCandidates(candidates: Array<string | Candidate>): this

  setPollInterval(interval: number): this
}

declare function DiscoveryClientFactory(
  options?: Partial<Options>
): DiscoveryClient

export default DiscoveryClientFactory
