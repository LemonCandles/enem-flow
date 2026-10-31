type Point = readonly [number, number];
type Curve = { from: Point; to: Point; controls?: readonly [Point, Point] };
type ProfileStep = { to: Point; controls?: readonly [Point, Point] };

// Coordinates along a 160-unit edge and perpendicular to it. Both profiles
// have a narrow neck and a wider head, rather than an arbitrary wavy side.
const round: readonly ProfileStep[] = [
  { to: [52, 0] },
  { to: [70, 6], controls: [[64, 0], [70, -2]] },
  { to: [62, 22], controls: [[70, 12], [62, 12]] },
  { to: [98, 22], controls: [[62, 42], [98, 42]] },
  { to: [90, 6], controls: [[98, 12], [90, 12]] },
  { to: [108, 0], controls: [[90, -2], [96, 0]] },
  { to: [160, 0] },
];
const broad: readonly ProfileStep[] = [
  { to: [48, 0] },
  { to: [69, 7], controls: [[64, 0], [69, -1]] },
  { to: [58, 23], controls: [[69, 13], [58, 13]] },
  { to: [80, 36], controls: [[58, 35], [68, 36]] },
  { to: [102, 23], controls: [[92, 36], [102, 35]] },
  { to: [91, 7], controls: [[102, 13], [91, 13]] },
  { to: [112, 0], controls: [[91, -1], [96, 0]] },
  { to: [160, 0] },
];

function edge(origin: Point, along: Point, outward: Point, profile: readonly ProfileStep[], insetStart = 0, insetEnd = 0): Curve[] {
  const map = ([u, v]: Point): Point => [origin[0] + along[0] * u + outward[0] * v, origin[1] + along[1] * u + outward[1] * v];
  let from = map([insetStart, 0]);
  return profile.map((step, index) => {
    const to = map(index === profile.length - 1 ? [160 - insetEnd, 0] : step.to);
    const result: Curve = { from, to, ...(step.controls ? { controls: [map(step.controls[0]), map(step.controls[1])] as const } : {}) };
    from = to;
    return result;
  });
}

function reverse(curves: readonly Curve[]): Curve[] {
  return [...curves].reverse().map(({ from, to, controls }) => ({ from: to, to: from, ...(controls ? { controls: [controls[1], controls[0]] as const } : {}) }));
}
const line = (from: Point, to: Point): Curve => ({ from, to });
const cubic = (from: Point, c1: Point, c2: Point, to: Point): Curve => ({ from, to, controls: [c1, c2] });
const point = (value: Point) => value.map(n => Number(n.toFixed(3))).join(' ');
const commands = (curves: readonly Curve[]) => curves.map(segment => segment.controls
  ? `C${point(segment.controls[0])} ${point(segment.controls[1])} ${point(segment.to)}`
  : `L${point(segment.to)}`).join(' ');
function path(curves: readonly Curve[], closed = false) {
  for (let i = 1; i < curves.length; i++) {
    if (point(curves[i - 1].to) !== point(curves[i].from)) throw new Error('O contorno da peça deve ser contínuo.');
  }
  if (closed && point(curves[0].from) !== point(curves[curves.length - 1].to)) throw new Error('O contorno da peça deve fechar.');
  return `M${point(curves[0].from)} ${commands(curves)}${closed ? ' Z' : ''}`;
}

// Each adjoining pair uses one shared boundary, traversed in opposite
// directions. Translating the pieces back to the grid makes the edges coincide.
const readingPractice = edge([180, 180], [1, 0], [0, -1], round);
const reasoningPractice = edge([180, 180], [0, 1], [1, 0], broad);
const readingLeft = edge([180, 20], [0, 1], [1, 0], round, 18);
const reasoningTop = edge([20, 180], [1, 0], [0, -1], broad, 18);
const practiceRight = edge([340, 180], [0, 1], [-1, 0], round, 0, 18);

export const PUZZLE_JOIN_PATHS = {
  readingPractice: path(readingPractice),
  reasoningPractice: path(reasoningPractice),
};

export const LEARNING_PIECES = [
  {
    id: 'reading', offset: [20, -18], accent: path(reverse(readingPractice)),
    outline: path([
      line([198, 20], [322, 20]),
      cubic([322, 20], [331.94, 20], [340, 28.06], [340, 38]),
      line([340, 38], [340, 180]),
      ...reverse(readingPractice), ...reverse(readingLeft),
      cubic([180, 38], [180, 28.06], [188.06, 20], [198, 20]),
    ], true),
  },
  {
    id: 'reasoning', offset: [-24, 30], accent: null,
    outline: path([
      ...reasoningTop, ...reasoningPractice,
      line([180, 340], [38, 340]),
      cubic([38, 340], [28.06, 340], [20, 331.94], [20, 322]),
      line([20, 322], [20, 198]),
      cubic([20, 198], [20, 188.06], [28.06, 180], [38, 180]),
    ], true),
  },
  {
    id: 'practice', offset: [20, 30], accent: path(readingPractice),
    outline: path([
      ...readingPractice, ...practiceRight,
      cubic([340, 322], [340, 331.94], [331.94, 340], [322, 340]),
      line([322, 340], [180, 340]), ...reverse(reasoningPractice),
    ], true),
  },
] as const;

export const BRAND_CONTOUR = `M2 2 L12 2 ${commands(edge([12, 2], [0, .2], [.2, 0], round))} L2 34`;
