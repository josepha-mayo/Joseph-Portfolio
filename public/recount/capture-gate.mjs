/* Protocol-state guard, independent of microphone, sockets, model, and stock writes.
   Messages in tests are authored fixtures, never presented as provider receipts. */
import {fromAssembly, normalizeTranscript} from './core.mjs';

export class CaptureGate {
  constructor({epoch, getRevision, onTurn, onHold, onPartial=()=>{}, onPhase=()=>{}}) {
    if(!Number.isSafeInteger(epoch)||epoch<1)throw Error('Invalid capture generation');
    Object.assign(this,{epoch,getRevision,onTurn,onHold,onPartial,onPhase});
    this.phase='connecting';this.session=null;this.lastOrder=-1;
    this.outstanding=null;this.finals=new Map();this.events=[];
  }
  locked(){return ['connecting','listening','draining'].includes(this.phase);}
  change(phase){this.phase=phase;this.onPhase(phase);}
  note(type,details={}){
    if(this.events.length>=1000){this.fail('invalid_event');return false;}
    this.events.push({type,...details});return true;
  }
  fail(reason){
    if(!this.locked())return;
    this.events.push({type:'hold',reason});this.change('faulted');this.onHold(reason);
  }
  beginSpeech(order=null){
    if(!this.outstanding)this.outstanding={order,revision:this.getRevision()};
    else if(order!==null)this.outstanding.order=order;
  }
  ingest(epoch,message){
    if(epoch!==this.epoch||!this.locked())return 'ignored_closed_generation';
    if(!message||typeof message.type!=='string'){this.fail('invalid_event');return;}
    // High-frequency partials update the display, not the count ledger or audit list.
    try {
      if(message.type==='Begin'){
        if(this.session || this.phase!=='connecting' || typeof message.id!=='string' || !/^[A-Za-z0-9:_-]{1,140}$/.test(message.id))throw Error('Invalid Begin');
        this.session=message.id;this.note('begin');this.change('listening');return 'begin';
      }
      if(!this.session)throw Error('Transcript before Begin');
      if(message.type==='SpeechStarted'){
        this.beginSpeech();return 'speech_started';
      }
      if(message.type==='Turn'){
        const order=message.turn_order;
        if(!Number.isSafeInteger(order)||order<0)throw Error('Invalid turn order');
        if(typeof message.transcript!=='string'||message.transcript.length>500)throw Error('Invalid transcript');
        if(message.end_of_turn!==true){
          if(order<=this.lastOrder)return 'ignored_late_partial';
          if(order!==this.lastOrder+1){this.fail('audio_gap');return;}
          this.beginSpeech(order);this.onPartial(message.transcript);return 'partial';
        }
        const action=fromAssembly(message,this.session,this.getRevision());
        const fingerprint=JSON.stringify([normalizeTranscript(action.text),action.confidence]);
        if(this.finals.has(order)){
          if(this.finals.get(order)!==fingerprint){this.fail('transcript_conflict');return;}
          return 'duplicate_final';
        }
        if(order!==this.lastOrder+1){this.fail('audio_gap');return;}
        if(this.outstanding && this.outstanding.revision!==this.getRevision()){
          this.fail('stale_turn');return;
        }
        action.revision=this.outstanding?.revision??this.getRevision();
        this.onTurn(action); // A rejected reducer operation must throw to this guard.
        this.finals.set(order,fingerprint);this.lastOrder=order;this.outstanding=null;
        this.onPartial('');this.note('final',{order});return 'final';
      }
      if(message.type==='Termination'){
        if(this.outstanding){this.fail('unfinished_speech');return;}
        this.note('termination',{final_turns:this.finals.size});this.change('closed');return 'terminated';
      }
      if(message.type==='Heartbeat')return 'heartbeat';
      // The selected request does not enable diarization or an LLM gateway.
      throw Error('Unexpected event');
    } catch(error) {
      this.fail(/Conflicting/.test(error.message)?'transcript_conflict':'invalid_event');
    }
  }
  requestStop(){
    if(this.phase==='listening'){this.note('stop_requested');this.change('draining');}
    else if(this.phase==='connecting')this.fail('stream_lost');
  }
  transportClosed(){if(this.locked())this.fail('stream_lost');}
  timeout(){if(this.locked())this.fail(this.outstanding?'unfinished_speech':'stream_lost');}
  revokeConsent(){if(this.locked())this.fail('consent_revoked');}
}
