// Execute the shipped calculator, without a browser or external dependencies.
// Reference values use Python's math.erf (independent of the JS approximation).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../tools/probabilistic-sharpe-ratio-calculator.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
const source = scripts.find(m => m[1].includes("var ids=['psr-sr'"))?.[1];
assert.ok(source, 'The built page must contain the calculator');
const defaults = {'psr-sr':'1.5','psr-bm':'0','psr-n':'24','psr-skew':'-1.2','psr-kurt':'7'};
function run(values = {}) {
  const nodes = {};
  for (const [id, value] of Object.entries({...defaults, ...values})) {
    nodes[id] = {value, addEventListener(event, callback) {this[event] = callback;}};
  }
  for (const id of ['psr-value', 'psr-verdict', 'psr-detail']) nodes[id] = {textContent:'',innerHTML:''};
  vm.runInNewContext(source, {document:{getElementById:id=>nodes[id]}});
  return nodes;
}
let passed = 0;
function test(name, fn) {fn(); passed++; console.log('PASS ' + name);}
test('Published example agrees with independent normal CDF', () => {
  const n = run();
  assert.equal(n['psr-value'].textContent, '99.81%');
  assert.match(n['psr-detail'].textContent, /denominator = 2.4850\s+z = 2.895/);
});
test('Stronger benchmark lowers the result', () => assert.equal(run({'psr-bm':'1'})['psr-value'].textContent, '83.27%'));
test('Observed Sharpe equal to benchmark gives 50%', () => assert.equal(run({'psr-bm':'1.5'})['psr-value'].textContent, '50.00%'));
test('Normal kurtosis still contributes to variance', () => assert.match(run({'psr-skew':'0','psr-kurt':'3'})['psr-detail'].textContent, /denominator = 1.4577/));
for (const [name, input] of [
  ['Missing input', {'psr-sr':''}],
  ['Infinite input', {'psr-sr':'Infinity'}],
  ['Overflowing variance', {'psr-sr':'1e308'}],
  ['Fractional observation count', {'psr-n':'24.5'}],
  ['Too few observations', {'psr-n':'1'}],
  ['Non-numeric input', {'psr-skew':'invalid'}],
  ['Non-positive variance', {'psr-skew':'3','psr-kurt':'3'}],
]) test(name + ' does not display a confidence result', () => assert.equal(run(input)['psr-value'].textContent, '—'));
test('Editing an input recalculates the displayed result', () => {
  const n = run(); n['psr-bm'].value='1'; n['psr-bm'].input();
  assert.equal(n['psr-value'].textContent, '83.27%');
});
console.log(`${passed} calculator checks passed`);
