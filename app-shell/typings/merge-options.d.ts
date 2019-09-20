// Type definitions for merge-options
// Project: https://github.com/schnittstabil/merge-options
// Definitions by: Opentrons Labworks <https://github.com/Opentrons>

declare module 'merge-options' {
  import { Node, Parent } from 'unist'

  function mergeOptions<R>(...sources: object[]): R

  export = mergeOptions
}
