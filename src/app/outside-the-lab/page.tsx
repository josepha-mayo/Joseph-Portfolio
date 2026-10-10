import { permanentRedirect } from 'next/navigation';

export default function OutsideTheLabRedirect() {
  permanentRedirect('/outside-the-work');
}
