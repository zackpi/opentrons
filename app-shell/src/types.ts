// TODO(mc, 2019-09-20): importing from app/index.d.ts directly to avoid
// confusing Jest; fix this by switching app/package.json::main to an exports
// file rather that the app entry-point (which is already set in webpack)
import { Action, PlainError, Config } from '@opentrons/app/index'

export { Action, PlainError, Config }

export type Dispatch = (action: Action) => void
