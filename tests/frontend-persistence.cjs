// Run the rendered application's actual functions against a minimal DOM/network fixture.
// This is a unit harness, not a browser or microphone acceptance test.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const pages = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
function fixture(enabled) {
    const elements = new Map();
    const timers = [];
    const requests = [];
    const node = id => {
        if (!elements.has(id)) elements.set(id, {style:{},textContent:'',innerHTML:'',disabled:false,
            classList:{add(){},remove(){},toggle(){}},addEventListener(){},reset(){},appendChild(){}});
        return elements.get(id);
    };
    const context = vm.createContext({console, document:{getElementById:node,querySelector:node,createElement:()=>node('created-'+elements.size)},
        window:{addEventListener(){}}, navigator:{},sessionStorage:{getItem(){return null},setItem(){},removeItem(){}},
        setTimeout(fn){timers.push(fn)},setInterval(){},clearInterval(){},alert(){},
        fetch:async (url, options) => {requests.push({url,options});throw new Error('offline')}
    });
    const script = pages[enabled ? 'true' : 'false']
        .match(/<script[^>]*>([\s\S]*?)<\/script>/)[1]
        .replace(/^        (loadMicrophones|restoreSession|startMetricsMonitoring|startLeaderboardPolling)\(\);$/gm, '');
    vm.runInContext(script, context);
    return {context,node,timers,requests,run:code=>vm.runInContext(code,context)};
}
(async () => {
    const f = fixture(true);
    f.run(`gameState = {difficulty:'hard',attempts:[],usedLanguages:['en'],currentAttemptIndex:0,
        swapsUsed:0,gameStarted:true,gameCompleted:false,gameId:42};
        currentChallenge={lang:'en',phrase:'Artificial intelligence transforms business'};`);
    await f.run(`recordAttempt('Artificial intelligence transforms business', 100)`);
    assert.equal(f.run('gameState.currentAttemptIndex'),0);
    assert.equal(f.run('gameState.attempts.length'),0);
    assert.equal(f.run('pendingAttempt.payload.attempt_index'),0);
    assert.equal(f.node('persistenceError').style.display,'block');
    assert.equal(f.node('recordBtn').disabled,true);
    f.run('resetGame(); changePlayer();');
    assert.equal(f.run('gameState.gameId'),42);
    const original = f.requests[0].options.body;
    f.context.fetch=async (url,options)=>{f.requests.push({url,options});return {ok:true,json:async()=>({accuracy:0.9,status:'win'})}};
    await f.run('retryPersistence()');
    assert.equal(f.requests[1].options.body,original);
    assert.equal(f.run('gameState.currentAttemptIndex'),1);
    assert.equal(f.run('gameState.attempts.length'),1);
    assert.equal(f.run('pendingAttempt'),null);
    assert.equal(f.node('persistenceError').style.display,'none');
    // No transition/recording before the saved round's display delay ends.
    assert.equal(f.node('recordBtn').disabled,true);
    f.run('gameState.currentAttemptIndex=5; gameState.attempts=Array(5).fill({score:100});currentChallenge=null;');
    f.context.fetch=async()=>({ok:false,status:503});
    await f.run('finishGame()');
    assert.equal(f.run('gameState.gameCompleted'),false);
    assert.equal(f.run('pendingCompletion'),true);
    assert.notEqual(f.node('congratsOverlay').style.display,'flex');
    assert.equal(f.node('persistenceError').style.display,'block');
    f.context.fetch=async url=>({ok:true,json:async()=>url.includes('leaderboard')?{leaderboard:[]}:
        {total_score:50,rank:1,best_score:50,is_new_best:true,won:false}});
    await f.run('retryPersistence()');
    assert.equal(f.run('gameState.gameCompleted'),true);
    assert.equal(f.node('lossOverlay').style.display,'flex'); // Use server result, not local 100%.
    assert.equal(f.run('pendingCompletion'),false);
    const standalone=fixture(false);
    await standalone.run('restoreSession()');
    await standalone.run('startGame("easy")');
    assert.equal(standalone.requests.length,0);
    assert.equal(standalone.run('gameState.gameId'),null);
    assert.equal(standalone.node('playerBadge').style.display,'none');
    await standalone.run('recordAttempt(currentChallenge.phrase,100)');
    assert.equal(standalone.run('gameState.currentAttemptIndex'),1);
    standalone.run('gameState.currentAttemptIndex=5;gameState.attempts=Array(5).fill({score:100});currentChallenge=null;');
    await standalone.run('finishGame()');
    assert.equal(standalone.requests.length,0);
    assert.equal(standalone.run('gameState.gameCompleted'),true);
    console.log('PASS: failed saves retain state, identical retries advance once, completion requires server confirmation, standalone makes no tournament requests');
})().catch(error=>{console.error(error);process.exitCode=1});
