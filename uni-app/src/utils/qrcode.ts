type Matrix = boolean[][]

const VERSION = 2
const SIZE = 21 + (VERSION - 1) * 4
const DATA_CODEWORDS = 34
const ECC_CODEWORDS = 10
const EC_LEVEL_L = 1

const GF_EXP = new Array<number>(512)
const GF_LOG = new Array<number>(256)

let x = 1
for (let i = 0; i < 255; i += 1) {
  GF_EXP[i] = x
  GF_LOG[x] = i
  x <<= 1
  if (x & 0x100) x ^= 0x11d
}
for (let i = 255; i < 512; i += 1) {
  GF_EXP[i] = GF_EXP[i - 255]
}

export function generateQrMatrix(content: string): Matrix {
  const data = encodeDataCodewords(content)
  const errorCorrection = ReedSolomon.encode(data, ECC_CODEWORDS)
  const codewords = [...data, ...errorCorrection]
  const base = createFunctionMatrix()
  const bits = codewords.flatMap(byteToBits)
  placeDataBits(base.modules, base.reserved, bits)

  let bestMatrix: Matrix | null = null
  let bestPenalty = Number.POSITIVE_INFINITY
  for (let mask = 0; mask < 8; mask += 1) {
    const candidate = cloneMatrix(base.modules)
    applyMask(candidate, base.reserved, mask)
    writeFormatBits(candidate, mask)
    const penalty = calculatePenalty(candidate)
    if (penalty < bestPenalty) {
      bestPenalty = penalty
      bestMatrix = candidate
    }
  }

  return bestMatrix || base.modules
}

class ReedSolomon {
  static encode(data: number[], degree: number): number[] {
    const generator = ReedSolomon.generator(degree)
    const result = new Array<number>(degree).fill(0)

    for (const value of data) {
      const factor = value ^ result.shift()!
      result.push(0)
      if (factor !== 0) {
        for (let i = 0; i < degree; i += 1) {
          result[i] ^= gfMultiply(generator[i], factor)
        }
      }
    }

    return result
  }

  private static generator(degree: number): number[] {
    let poly = [1]
    for (let i = 0; i < degree; i += 1) {
      const next = new Array<number>(poly.length + 1).fill(0)
      for (let j = 0; j < poly.length; j += 1) {
        next[j] ^= poly[j]
        next[j + 1] ^= gfMultiply(poly[j], GF_EXP[i])
      }
      poly = next
    }
    return poly.slice(1)
  }
}

function encodeDataCodewords(content: string): number[] {
  const bytes = asciiBytes(content)
  if (bytes.length > 32) {
    throw new Error('二维码内容过长')
  }

  const bits: number[] = []
  appendBits(bits, 0b0100, 4)
  appendBits(bits, bytes.length, 8)
  for (const byte of bytes) {
    appendBits(bits, byte, 8)
  }

  const capacityBits = DATA_CODEWORDS * 8
  appendBits(bits, 0, Math.min(4, capacityBits - bits.length))
  while (bits.length % 8 !== 0) bits.push(0)

  const data: number[] = []
  for (let i = 0; i < bits.length; i += 8) {
    data.push(bitsToByte(bits.slice(i, i + 8)))
  }
  for (let pad = 0xec; data.length < DATA_CODEWORDS; pad = pad === 0xec ? 0x11 : 0xec) {
    data.push(pad)
  }
  return data
}

function asciiBytes(content: string): number[] {
  const bytes: number[] = []
  for (let i = 0; i < content.length; i += 1) {
    const code = content.charCodeAt(i)
    if (code > 0xff) {
      throw new Error('二维码仅支持 ASCII 内容')
    }
    bytes.push(code)
  }
  return bytes
}

function createFunctionMatrix(): { modules: Matrix; reserved: Matrix } {
  const modules = createMatrix(false)
  const reserved = createMatrix(false)

  drawFinder(modules, reserved, 0, 0)
  drawFinder(modules, reserved, SIZE - 7, 0)
  drawFinder(modules, reserved, 0, SIZE - 7)
  drawTiming(modules, reserved)
  drawAlignment(modules, reserved, 18, 18)
  reserveFormatAreas(reserved)
  setReserved(modules, reserved, 8, SIZE - 8, true)

  return { modules, reserved }
}

function drawFinder(modules: Matrix, reserved: Matrix, left: number, top: number): void {
  for (let y = -1; y <= 7; y += 1) {
    for (let x = -1; x <= 7; x += 1) {
      const col = left + x
      const row = top + y
      if (!inBounds(row, col)) continue
      const isPattern = x >= 0 && x <= 6 && y >= 0 && y <= 6
      const isDark = isPattern && (
        x === 0 ||
        x === 6 ||
        y === 0 ||
        y === 6 ||
        (x >= 2 && x <= 4 && y >= 2 && y <= 4)
      )
      setReserved(modules, reserved, row, col, isDark)
    }
  }
}

function drawTiming(modules: Matrix, reserved: Matrix): void {
  for (let i = 8; i < SIZE - 8; i += 1) {
    const isDark = i % 2 === 0
    setReserved(modules, reserved, 6, i, isDark)
    setReserved(modules, reserved, i, 6, isDark)
  }
}

function drawAlignment(modules: Matrix, reserved: Matrix, centerCol: number, centerRow: number): void {
  for (let y = -2; y <= 2; y += 1) {
    for (let x = -2; x <= 2; x += 1) {
      const isDark = Math.max(Math.abs(x), Math.abs(y)) === 2 || (x === 0 && y === 0)
      setReserved(modules, reserved, centerRow + y, centerCol + x, isDark)
    }
  }
}

function reserveFormatAreas(reserved: Matrix): void {
  for (let i = 0; i <= 5; i += 1) markReserved(reserved, i, 8)
  markReserved(reserved, 7, 8)
  markReserved(reserved, 8, 8)
  markReserved(reserved, 8, 7)
  for (let i = 9; i < 15; i += 1) markReserved(reserved, 8, 14 - i)
  for (let i = 0; i < 8; i += 1) markReserved(reserved, 8, SIZE - 1 - i)
  for (let i = 8; i < 15; i += 1) markReserved(reserved, SIZE - 15 + i, 8)
  markReserved(reserved, SIZE - 8, 8)
}

function placeDataBits(modules: Matrix, reserved: Matrix, bits: number[]): void {
  let bitIndex = 0
  let upward = true

  for (let right = SIZE - 1; right >= 1; right -= 2) {
    if (right === 6) right -= 1
    for (let vert = 0; vert < SIZE; vert += 1) {
      const row = upward ? SIZE - 1 - vert : vert
      for (let offset = 0; offset < 2; offset += 1) {
        const col = right - offset
        if (reserved[row][col]) continue
        modules[row][col] = bitIndex < bits.length ? bits[bitIndex] === 1 : false
        bitIndex += 1
      }
    }
    upward = !upward
  }
}

function applyMask(modules: Matrix, reserved: Matrix, mask: number): void {
  for (let row = 0; row < SIZE; row += 1) {
    for (let col = 0; col < SIZE; col += 1) {
      if (!reserved[row][col] && maskPredicate(mask, row, col)) {
        modules[row][col] = !modules[row][col]
      }
    }
  }
}

function maskPredicate(mask: number, row: number, col: number): boolean {
  switch (mask) {
    case 0: return (row + col) % 2 === 0
    case 1: return row % 2 === 0
    case 2: return col % 3 === 0
    case 3: return (row + col) % 3 === 0
    case 4: return (Math.floor(row / 2) + Math.floor(col / 3)) % 2 === 0
    case 5: return ((row * col) % 2) + ((row * col) % 3) === 0
    case 6: return (((row * col) % 2) + ((row * col) % 3)) % 2 === 0
    case 7: return (((row + col) % 2) + ((row * col) % 3)) % 2 === 0
    default: return false
  }
}

function writeFormatBits(modules: Matrix, mask: number): void {
  const bits = getFormatBits(mask)
  for (let i = 0; i <= 5; i += 1) setModule(modules, i, 8, bitAt(bits, i))
  setModule(modules, 7, 8, bitAt(bits, 6))
  setModule(modules, 8, 8, bitAt(bits, 7))
  setModule(modules, 8, 7, bitAt(bits, 8))
  for (let i = 9; i < 15; i += 1) setModule(modules, 8, 14 - i, bitAt(bits, i))
  for (let i = 0; i < 8; i += 1) setModule(modules, 8, SIZE - 1 - i, bitAt(bits, i))
  for (let i = 8; i < 15; i += 1) setModule(modules, SIZE - 15 + i, 8, bitAt(bits, i))
  setModule(modules, SIZE - 8, 8, true)
}

function getFormatBits(mask: number): number {
  const data = (EC_LEVEL_L << 3) | mask
  let bits = data << 10
  const generator = 0x537
  for (let i = 14; i >= 10; i -= 1) {
    if (((bits >> i) & 1) !== 0) {
      bits ^= generator << (i - 10)
    }
  }
  return (((data << 10) | bits) ^ 0x5412) & 0x7fff
}

function calculatePenalty(modules: Matrix): number {
  let penalty = 0
  penalty += adjacentPenalty(modules, true)
  penalty += adjacentPenalty(modules, false)
  penalty += blockPenalty(modules)
  penalty += finderLikePenalty(modules, true)
  penalty += finderLikePenalty(modules, false)
  penalty += balancePenalty(modules)
  return penalty
}

function adjacentPenalty(modules: Matrix, horizontal: boolean): number {
  let penalty = 0
  for (let outer = 0; outer < SIZE; outer += 1) {
    let runColor = false
    let runLength = 0
    for (let inner = 0; inner < SIZE; inner += 1) {
      const value = horizontal ? modules[outer][inner] : modules[inner][outer]
      if (inner === 0 || value !== runColor) {
        runColor = value
        runLength = 1
      } else {
        runLength += 1
        if (runLength === 5) penalty += 3
        else if (runLength > 5) penalty += 1
      }
    }
  }
  return penalty
}

function blockPenalty(modules: Matrix): number {
  let penalty = 0
  for (let row = 0; row < SIZE - 1; row += 1) {
    for (let col = 0; col < SIZE - 1; col += 1) {
      const color = modules[row][col]
      if (
        color === modules[row][col + 1] &&
        color === modules[row + 1][col] &&
        color === modules[row + 1][col + 1]
      ) {
        penalty += 3
      }
    }
  }
  return penalty
}

function finderLikePenalty(modules: Matrix, horizontal: boolean): number {
  let penalty = 0
  const pattern = [true, false, true, true, true, false, true, false, false, false, false]
  const inverse = [false, false, false, false, true, false, true, true, true, false, true]
  for (let outer = 0; outer < SIZE; outer += 1) {
    for (let inner = 0; inner <= SIZE - pattern.length; inner += 1) {
      const values = pattern.map((_, i) => horizontal ? modules[outer][inner + i] : modules[inner + i][outer])
      if (matches(values, pattern) || matches(values, inverse)) {
        penalty += 40
      }
    }
  }
  return penalty
}

function balancePenalty(modules: Matrix): number {
  let dark = 0
  for (const row of modules) {
    for (const cell of row) {
      if (cell) dark += 1
    }
  }
  const total = SIZE * SIZE
  const k = Math.ceil(Math.abs(dark * 20 - total * 10) / total) - 1
  return Math.max(0, k) * 10
}

function gfMultiply(a: number, b: number): number {
  if (a === 0 || b === 0) return 0
  return GF_EXP[GF_LOG[a] + GF_LOG[b]]
}

function appendBits(bits: number[], value: number, length: number): void {
  for (let i = length - 1; i >= 0; i -= 1) {
    bits.push((value >> i) & 1)
  }
}

function byteToBits(value: number): number[] {
  const bits: number[] = []
  appendBits(bits, value, 8)
  return bits
}

function bitsToByte(bits: number[]): number {
  return bits.reduce((value, bit) => (value << 1) | bit, 0)
}

function bitAt(value: number, index: number): boolean {
  return ((value >> index) & 1) !== 0
}

function createMatrix(value: boolean): Matrix {
  return Array.from({ length: SIZE }, () => new Array<boolean>(SIZE).fill(value))
}

function cloneMatrix(matrix: Matrix): Matrix {
  return matrix.map(row => row.slice())
}

function setReserved(modules: Matrix, reserved: Matrix, row: number, col: number, value: boolean): void {
  if (!inBounds(row, col)) return
  modules[row][col] = value
  reserved[row][col] = true
}

function markReserved(reserved: Matrix, row: number, col: number): void {
  if (inBounds(row, col)) reserved[row][col] = true
}

function setModule(modules: Matrix, row: number, col: number, value: boolean): void {
  if (inBounds(row, col)) modules[row][col] = value
}

function inBounds(row: number, col: number): boolean {
  return row >= 0 && row < SIZE && col >= 0 && col < SIZE
}

function matches(values: boolean[], pattern: boolean[]): boolean {
  return values.every((value, index) => value === pattern[index])
}
