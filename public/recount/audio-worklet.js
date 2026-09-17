class PCM16 extends AudioWorkletProcessor {
  constructor(){super();this.samples=[];this.stopped=false;
    this.port.onmessage=e=>{if(e.data?.type==='flush'){
      this.stopped=true;this.emit();this.port.postMessage({type:'flushed'});
    }};
  }
  emit(){
    if(!this.samples.length)return;
    const buffer=new ArrayBuffer(this.samples.length*2),view=new DataView(buffer);
    this.samples.forEach((v,i)=>view.setInt16(i*2,Math.round(v*(v<0?32768:32767)),true));
    this.samples=[];this.port.postMessage(buffer,[buffer]);
  }
  process(inputs){
    if(this.stopped)return true;
    const x=inputs[0]?.[0];if(x){for(const v of x){
      if(!Number.isFinite(v)){this.stopped=true;this.samples=[];this.port.postMessage({type:'fault'});return true;}
      this.samples.push(Math.max(-1,Math.min(1,v)));
    }}
    if(this.samples.length>=sampleRate/10)this.emit();return true;
  }
}
registerProcessor('recount-pcm16',PCM16);
