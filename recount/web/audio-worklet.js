class PCM16 extends AudioWorkletProcessor {
  constructor(){super();this.samples=[];}
  process(inputs){const x=inputs[0]?.[0];if(x){for(const v of x)this.samples.push(Math.max(-1,Math.min(1,v)));}
    if(this.samples.length>=sampleRate/10){const buffer=new ArrayBuffer(this.samples.length*2),view=new DataView(buffer);this.samples.forEach((v,i)=>view.setInt16(i*2,Math.round(v*(v<0?32768:32767)),true));this.port.postMessage(buffer,[buffer]);this.samples=[];}return true;}
}
registerProcessor('recount-pcm16',PCM16);
