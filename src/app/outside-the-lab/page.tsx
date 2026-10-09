import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import LifePhilosophy from '@/components/LifePhilosophy';
import styles from './personal.module.css';

export const metadata: Metadata = {
  title: 'outside the lab | ayanda joseph',
  description: 'the other side of ayanda joseph: books, japanese, guitar, chess, a few thoughts on life, and the anime that changed me positively.',
  alternates: { canonical: 'https://josephmayo.site/outside-the-lab' },
  openGraph: { title: 'outside the lab | ayanda joseph', description: 'books, practice, and stories that left something with me.', url: 'https://josephmayo.site/outside-the-lab', type: 'website' },
};

const books = [
  { title: 'the myth of sisyphus', author: 'albert camus', kind: 'philosophy' },
  { title: 'crime and punishment', author: 'fyodor dostoevsky', kind: 'fiction' },
  { title: 'the brothers karamazov', author: 'fyodor dostoevsky', kind: 'fiction' },
  { title: 'the computer and the brain', author: 'john von neumann', kind: 'mind & machines' },
  { title: 'the metamorphosis', author: 'franz kafka', kind: 'fiction' },
  { title: 'beyond good and evil', author: 'friedrich nietzsche', kind: 'philosophy' },
  { title: 'man’s search for meaning', author: 'viktor e. frankl', kind: 'meaning & psychology' },
];
const practices = [
  { title: 'japanese', status: 'learning', image: '/personal/japanese.jpg', alt: 'japanese writing in everyday life', icon: 'fa-language', text: 'back to being a beginner. a little more japanese, a little less reaching for the translation. there’s a long way to go, and that’s fine.' },
  { title: 'guitar', status: 'learning', image: '/personal/guitar.jpg', alt: 'an acoustic guitar', icon: 'fa-guitar', text: 'getting the chord changes cleaner and the rhythm steadier. a different kind of practice from sitting behind a keyboard.' },
  { title: 'chess', status: 'i play', image: '/personal/chess.jpg', alt: 'chess pieces on a board', icon: 'fa-chess-knight', text: 'not a beginner at this one. i’m a good player, and i enjoy a proper game. especially when there’s something interesting to calculate.' },
];
const stories = [
  { title: 'hajime no ippo', note: 'the work adds up', number: '02', text: 'getting better isn’t always dramatic. sometimes it’s the same drill again, one small improvement at a time. ippo made that part feel worth doing.' },
  { title: 'dr. stone', note: 'senku, obviously', number: '03', text: 'curiosity that actually turns into something. ask why, try it, get it wrong, figure it out. senku makes me want to learn more and build things.' },
  { title: 'kaiji', note: 'think before you go all-in', number: '04', text: 'the psychology, the pressure, the way people act when the stakes get real. it makes me question the rules of the game, not just how to win it.' },
  { title: 'major', note: 'stay with the long road', number: '05', text: 'ambition over the long haul. setbacks, starting over, and still wanting to get better. i like seeing the whole road, not just the victory at the end.' },
];
function SectionHeading({ number, title, children }: { number: string; title: string; children?: React.ReactNode }) {
  return <div className={styles.sectionHeading}><span className={styles.sectionNumber}>{number}</span><div><h2>{title}</h2>{children && <p>{children}</p>}</div></div>;
}

export default function OutsideTheLab() {
  return (
    <div className={styles.page}>
      <nav className="fixed top-0 w-full h-[70px] nav-glass border-b border-border-subtle z-50 flex items-center" aria-label="personal page">
        <div className="container mx-auto px-6 md:px-8 flex justify-between items-center">
          <Link href="/" className="font-display text-2xl font-bold text-text-primary" aria-label="ayanda joseph, home">aj<span className="text-accent">.</span></Link>
          <Link href="/" className={styles.backLink}><span aria-hidden="true">←</span> back to the work</Link>
        </div>
      </nav>
      <main id="main">
        <header className={styles.hero}>
          <div className={styles.heroBackdrop} aria-hidden="true"><Image src="/personal/river.avif" alt="" fill sizes="100vw" priority className={styles.riverImage} /></div>
          <div className={styles.heroShade} aria-hidden="true" />
          <div className={`${styles.container} ${styles.heroContent}`}>
            <p className={styles.eyebrow}><span className={styles.smallSquare} aria-hidden="true" />ayanda joseph / the other side</p>
            <h1>outside<br />the lab<span className={styles.accent}>.</span></h1>
            <p className={styles.heroIntro}>i spend a lot of time with code.<br />this is everything else i’m making room for.</p>
            <nav aria-label="on this page" className={styles.chapterNav}>
              <a href="#books"><span>01</span> the shelf</a><a href="#practice"><span>02</span> practice</a><a href="#philosophy"><span>03</span> life</a><a href="#stories"><span>04</span> stories</a>
            </nav>
          </div>
          <p className={styles.heroFootnote}>not a résumé. just a bit more of me.</p>
        </header>
        <section id="books" className={`${styles.container} ${styles.section}`} aria-label="books i have read and am reading">
          <SectionHeading number="01" title="the shelf">books i’ve read and books i’m reading. some finished, some still open.</SectionHeading>
          <div className={styles.bookGrid}>{books.map((book, index) => (
            <article key={book.title} className={styles.book}>
              <span className={styles.bookNumber}>{String(index + 1).padStart(2, '0')}</span><div className={styles.bookText}><h3>{book.title}</h3><p>{book.author}</p></div><span className={styles.bookKind}>{book.kind}</span>
            </article>
          ))}</div>
          <p className={styles.shelfNote}>a lot of questions about being human. one detour into the brain.</p>
        </section>
        <section id="practice" className={`${styles.container} ${styles.section}`} aria-label="learning and hobbies">
          <SectionHeading number="02" title="a different kind of practice">two things i’m learning. one i already play well.</SectionHeading>
          <div className={styles.practiceGrid}>{practices.map((practice) => (
            <article key={practice.title} className={styles.practiceCard}>
              <div className={styles.practiceImage}><Image src={practice.image} alt={practice.alt} fill sizes="(min-width: 900px) 33vw, (min-width: 640px) 50vw, 100vw" /><span className={styles.practiceStatus}>{practice.status}</span></div>
              <div className={styles.practiceCopy}><h3><i className={`fa-solid ${practice.icon}`} aria-hidden="true" />{practice.title}</h3><p>{practice.text}</p></div>
            </article>
          ))}</div>
        </section>
        <section id="philosophy" className={`${styles.container} ${styles.section}`} aria-label="my philosophy on life">
          <div className={styles.philosophyPanel}><span className={styles.philosophyNumber} aria-hidden="true">03 / life</span><LifePhilosophy /></div>
        </section>
        <section id="stories" className={`${styles.container} ${styles.section}`} aria-label="anime i recommend">
          <SectionHeading number="04" title="stories that stayed with me">i recommend these. they changed me positively, and not just while i was watching.</SectionHeading>
          <article className={styles.joeFeature}>
            <div className={styles.joeImage}><Image src="/personal/joe.avif" alt="joe yabuki from ashita no joe, smiling beneath an orange sky" fill sizes="(min-width: 900px) 400px, (min-width: 640px) 40vw, 100vw" /></div>
            <div className={styles.joeCopy}><p className={styles.eyebrow}>01 / my favourite</p><h3>ashita no joe</h3><p>more than an anime to me. the pride, the losses, the determination, and finding something that gives your life meaning.</p><p>it changed how i think about purpose and what i’m willing to put into the things i care about. this is the one i’d recommend first.</p><span className={styles.recommended}><span aria-hidden="true">↗</span> personally recommended</span></div>
          </article>
          <div className={styles.storyGrid}>{stories.map((story) => (
            <article key={story.title} className={styles.storyCard}><div className={styles.storyTop}><span>{story.number}</span><span>recommended</span></div><h3>{story.title}</h3><p className={styles.storyNote}>{story.note}</p><p>{story.text}</p></article>
          ))}</div>
        </section>
      </main>
      <footer className={styles.footer}>
        <div className={styles.container}>
          <p className={styles.eyebrow}>the work is only part of it.</p><h2>that’s a bit more of me.</h2>
          <div className={styles.footerLinks}><Link href="/" className={styles.primaryLink}>back to the work <span aria-hidden="true">↗</span></Link><Link href="/#contact" className={styles.backLink}>say hello <span aria-hidden="true">↗</span></Link></div>
          <div className={styles.footerBottom}><p>© {new Date().getFullYear()} ayanda joseph. still becoming.</p><details className={styles.credits}><summary>image credits</summary><div><p>joe illustration: supplied image of joe yabuki. artist not identified.</p><p>river photograph: kris lückenbach, credited in the supplied image.</p><p>practice photos on unsplash: <a href="https://unsplash.com/photos/text-8iltjzxR2ns" target="_blank" rel="noopener noreferrer">flyd</a>, <a href="https://unsplash.com/photos/brown-acoustic-guitar-on-brown-wooden-floor-4cJTiLAL6M4" target="_blank" rel="noopener noreferrer">isa bauptista</a>, and <a href="https://unsplash.com/photos/chess-pieces-on-board-nAjil1z3eLk" target="_blank" rel="noopener noreferrer">felix mittermeier</a>.</p></div></details></div>
        </div>
      </footer>
    </div>
  );
}
