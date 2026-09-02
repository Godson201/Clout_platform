"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import {
  BarChart3,
  Bot,
  CheckCircle2,
  Handshake,
  MapPin,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  Video,
  Wallet,
} from "lucide-react";

import { PremiumGradientBackground } from "@/components/marketing/premium-gradient-background";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuthStore } from "@/store/auth-store";

const NAV_LINKS = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#benefits", label: "Benefits" },
  { href: "#payments", label: "Payments" },
  { href: "#why-clout", label: "Why CLOUT" },
];

function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-brand-navy/40 text-white backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <img src="/clout-logo.png" alt="CLOUT" className="h-8 w-auto" />
        <nav className="hidden items-center gap-6 text-sm text-white/80 md:flex">
          {NAV_LINKS.map((link) => (
            <a key={link.href} href={link.href} className="transition-colors hover:text-brand-teal">
              {link.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle className="border-white/30 bg-transparent text-white hover:bg-white/10" />
          <Button
            size="sm"
            variant="outline"
            className="border-white/40 bg-transparent text-white hover:bg-white/10"
            render={<Link href="/login" />}
          >
            Log in
          </Button>
          <Button size="sm" render={<Link href="/register" />}>
            Get started
          </Button>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative isolate flex min-h-[calc(100vh-4rem)] items-center overflow-hidden px-6 py-20 text-center">
      <Image
        src="/images/clout-hero-creator-v1.png"
        alt="A creator recording a product campaign with her phone"
        fill
        priority
        quality={90}
        sizes="100vw"
        className="object-cover object-[68%_center] sm:object-center"
      />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(3,22,38,0.72)_0%,rgba(3,22,38,0.38)_44%,rgba(3,22,38,0.05)_72%)]" />
      <div className="relative z-10 mx-auto max-w-3xl animate-fade-in">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-white/90 backdrop-blur-sm">
          <Sparkles className="size-3.5 text-brand-teal" />
          Influencer marketing, built for Rwanda
        </span>
        <h1 className="mt-6 text-4xl font-semibold tracking-tight text-balance text-white sm:text-5xl lg:text-6xl">
          Where brands and influencers actually get results — together.
        </h1>
        <p className="mt-5 text-lg text-white/80 text-balance">
          CLOUT connects brands with real, local influencers — from campaign creation and secure MTN MoMo
          payment, to publishing, performance tracking, and getting paid. One platform, start to finish.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Button size="lg" render={<Link href="/register?type=brand" />}>
            Join as a brand
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="border-white/40 bg-transparent text-white hover:bg-white/10"
            render={<Link href="/register?type=influencer" />}
          >
            Join as a creator
          </Button>
        </div>
        <p className="mt-4 text-sm text-white/70">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-brand-teal underline underline-offset-4">
            Log in
          </Link>
        </p>
      </div>
    </section>
  );
}

function VisualStories() {
  return (
    <section className="overflow-hidden bg-brand-navy px-6 py-20 text-white">
      <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-[1fr_0.9fr]">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-white/90">
            <Video className="size-3.5 text-brand-teal" />
            Made for the way content moves
          </span>
          <h2 className="mt-5 text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            Turn a brand brief into a video people want to watch.
          </h2>
          <p className="mt-4 max-w-xl text-white/75">
            Brands add approved campaign media. Creators make an authentic short ad with it. Then CLOUT puts the
            finished story in front of the right audience.
          </p>
          <div className="mt-7 grid gap-3 sm:grid-cols-3">
            {[
              ["1", "Choose", "Find a brief that fits your audience."],
              ["2", "Create", "Use media from the toolkit or your own."],
              ["3", "Share", "Publish a short, watchable campaign."],
            ].map(([number, title, body]) => (
              <div key={number} className="rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur-sm">
                <span className="text-sm font-semibold text-brand-teal">{number}</span>
                <h3 className="mt-2 font-medium">{title}</h3>
                <p className="mt-1 text-xs leading-5 text-white/65">{body}</p>
              </div>
            ))}
          </div>
          <Button className="mt-8" size="lg" render={<Link href="/register?type=influencer" />}>
            Explore as a creator
          </Button>
        </div>
        <div className="relative mx-auto w-full max-w-md">
          <div className="absolute -inset-8 rounded-full bg-brand-teal/30 blur-3xl" />
          <div className="relative overflow-hidden rounded-[2rem] border border-white/20 bg-white/10 p-2 shadow-2xl">
            <Image
              src="/images/clout-creator-studio-v1.png"
              alt="A creator producing a product video in a studio"
              width={1122}
              height={1400}
              quality={90}
              sizes="(max-width: 768px) 90vw, 420px"
              className="aspect-[4/5] w-full rounded-[1.5rem] object-cover animate-[clout-visual-drift_8s_ease-in-out_infinite]"
            />
            <div className="absolute bottom-6 left-6 right-6 rounded-2xl border border-white/20 bg-brand-navy/75 px-4 py-3 backdrop-blur-md">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-brand-teal">Creator studio</p>
              <p className="mt-1 text-sm text-white/90">A real campaign can feel native, useful, and worth sharing.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const STEPS = [
  {
    title: "Create your account",
    body: "Register as a brand or a creator in minutes. Verify your email, set your niche, and place your real location on the map — down to your sector and cell.",
  },
  {
    title: "Build or browse campaigns",
    body: "Brands pick a template and build a platform-ready ad with the Brand Toolkit. Creators browse open slots matched to their niche, location, and audience.",
  },
  {
    title: "Fund & claim, safely",
    body: "Brands fund the campaign via MTN MoMo — held in secure escrow. Creators claim a matching slot and post the ad to their account.",
  },
  {
    title: "Deliver, track, get paid",
    body: "Performance is tracked automatically as it comes in. Once delivery is verified, escrow releases and creators are paid out straight to MoMo.",
  },
];

function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-border bg-muted/40 px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight">How CLOUT works</h2>
          <p className="mt-3 text-muted-foreground">
            The same four steps, whether you&apos;re funding a campaign or delivering one.
          </p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => (
            <Card key={step.title} className="border-border">
              <CardContent className="pt-6">
                <span className="flex size-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                  {i + 1}
                </span>
                <h3 className="mt-4 font-medium">{step.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{step.body}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

const BRAND_BENEFITS = [
  "Reach real, verified local influencers matched to your sector and location",
  "Build platform-ready ads fast with the built-in Brand Toolkit — no agency needed",
  "Pay safely: funds sit in MTN MoMo escrow, released only on verified delivery",
  "Get AI-assisted campaign reports and comment sentiment analysis automatically",
  "Full transparency — see exactly who posted what, and how it performed",
];

const INFLUENCER_BENEFITS = [
  "Get discovered by brands actively looking for creators like you",
  "Claim paid campaign slots that match your niche, location, and audience",
  "Get paid reliably straight to MTN MoMo once you deliver",
  "Build a track record that unlocks better-matched, higher-paying campaigns",
  "Manage everything in one place — connect accounts, post, and track performance",
];

function BenefitList({ title, items, href, cta }: { title: string; items: string[]; href: string; cta: string }) {
  return (
    <Card className="border-border">
      <CardContent className="space-y-4 pt-6">
        <h3 className="text-xl font-semibold">{title}</h3>
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm text-muted-foreground">
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
        <Button variant="outline" render={<Link href={href} />}>
          {cta}
        </Button>
      </CardContent>
    </Card>
  );
}

function Benefits() {
  return (
    <section id="benefits" className="px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight">Built for both sides of the deal</h2>
          <p className="mt-3 text-muted-foreground">Whichever side you&apos;re on, CLOUT is built around you.</p>
        </div>
        <div className="mt-12 grid gap-6 md:grid-cols-2">
          <BenefitList title="For brands" items={BRAND_BENEFITS} href="/register?type=brand" cta="Start a campaign" />
          <BenefitList
            title="For influencers"
            items={INFLUENCER_BENEFITS}
            href="/register?type=influencer"
            cta="Start earning"
          />
        </div>
      </div>
    </section>
  );
}

const WHY_CLOUT = [
  {
    icon: ShieldCheck,
    title: "Secure MTN MoMo escrow",
    body: "Campaign funds are never released to influencers until delivery is verified — protecting both sides of every deal.",
  },
  {
    icon: MapPin,
    title: "Real Rwanda location data",
    body: "Precise province-to-village matching and a live map on every profile, not vague city guesses.",
  },
  {
    icon: Bot,
    title: "AI-powered insights",
    body: "Comment sentiment analysis and auto-generated campaign reports, built from verified performance data.",
  },
  {
    icon: Handshake,
    title: "Explainable matching",
    body: "Influencers are matched by sector, location, tier, and track record — a transparent score, not a black box.",
  },
  {
    icon: Video,
    title: "Built-in Brand Toolkit",
    body: "Create a platform-ready ad from a template in minutes — no agency or design team required.",
  },
  {
    icon: RefreshCcw,
    title: "Automatic recovery",
    body: "Undelivered campaign budget is recycled to a new creator or refunded — brands never just lose the spend.",
  },
];

function WhyClout() {
  return (
    <section id="why-clout" className="border-t border-border bg-muted/40 px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight">Why choose CLOUT</h2>
          <p className="mt-3 text-muted-foreground">Everything an influencer campaign needs, verified end to end.</p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {WHY_CLOUT.map(({ icon: Icon, title, body }) => (
            <div
              key={title}
              className="premium-card-hover rounded-[18px] border border-border bg-card p-5 shadow-[0_4px_24px_rgba(0,0,0,0.12)]"
            >
              <span className="flex size-10 items-center justify-center rounded-full bg-accent">
                <Icon className="size-5 text-accent-foreground" />
              </span>
              <h3 className="mt-3 font-medium">{title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function PaymentsSection() {
  return (
    <section id="payments" className="px-6 py-20">
      <div className="mx-auto max-w-6xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight">Money, handled properly</h2>
          <p className="mt-3 text-muted-foreground">Every shilling is tracked — from MoMo payment to MoMo payout.</p>
        </div>
        <div className="mt-12 grid gap-8 md:grid-cols-2">
          <Card className="border-border">
            <CardContent className="space-y-4 pt-6">
              <div className="flex items-center gap-2">
                <Wallet className="size-5 text-primary" />
                <h3 className="text-lg font-semibold">How to pay (brands)</h3>
              </div>
              <ol className="space-y-3 text-sm text-muted-foreground">
                <li><span className="font-medium text-foreground">1. Create and price a campaign</span> — pick your ad, target views, tier, and influencer count.</li>
                <li><span className="font-medium text-foreground">2. Pay via MTN MoMo</span> — enter your number and confirm the payment prompt on your phone.</li>
                <li><span className="font-medium text-foreground">3. Funds sit in escrow</span> — nothing is paid out until delivery actually happens.</li>
                <li><span className="font-medium text-foreground">4. Released as verified</span> — with automatic refunds for any shortfall.</li>
              </ol>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="space-y-4 pt-6">
              <div className="flex items-center gap-2">
                <BarChart3 className="size-5 text-success" />
                <h3 className="text-lg font-semibold">How to earn (influencers)</h3>
              </div>
              <ol className="space-y-3 text-sm text-muted-foreground">
                <li><span className="font-medium text-foreground">1. Connect your accounts</span> — TikTok, Instagram, Facebook, or YouTube.</li>
                <li><span className="font-medium text-foreground">2. Claim a matched slot</span> — up to 5 active campaigns at once.</li>
                <li><span className="font-medium text-foreground">3. Post and submit</span> — publish the ad and confirm your live post.</li>
                <li><span className="font-medium text-foreground">4. Get paid to MoMo</span> — once your delivery is confirmed, request your payout any time.</li>
              </ol>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}

function MotivationBanner() {
  return (
    <section className="relative isolate overflow-hidden px-6 py-20 text-center text-white">
      <Image
        src="/images/clout-registration-collaboration-v1.png"
        alt=""
        fill
        quality={90}
        sizes="100vw"
        className="object-cover object-[68%_center]"
      />
      <PremiumGradientBackground photoBehind />
      <div className="relative z-10 mx-auto max-w-2xl animate-fade-in">
        <h2 className="text-3xl font-semibold text-balance sm:text-4xl">
          Your next big brand deal — or your next great creator — is one click away.
        </h2>
        <p className="mt-3 text-white/80">
          No agencies, no guesswork, no waiting around for payment. Just real campaigns, real creators, real
          results.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Button size="lg" variant="secondary" render={<Link href="/register" />}>
            Create your free account
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="border-white/40 bg-transparent text-white hover:bg-white/10"
            render={<Link href="/login" />}
          >
            Log in
          </Button>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-sidebar-border bg-sidebar px-6 py-10 text-sidebar-foreground">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-sm sm:flex-row">
        <div>
          <img src="/clout-logo.png" alt="CLOUT" className="h-7 w-auto" />
          <p className="mt-2 text-sidebar-foreground/70">Influencer marketing & ad distribution, built for Rwanda.</p>
        </div>
        <div className="flex items-center gap-5 text-sidebar-foreground/80">
          <a href="#how-it-works" className="hover:text-sidebar-foreground">How it works</a>
          <a href="#benefits" className="hover:text-sidebar-foreground">Benefits</a>
          <Link href="/login" className="hover:text-sidebar-foreground">Log in</Link>
          <Link href="/register" className="hover:text-sidebar-foreground">Register</Link>
        </div>
      </div>
      <p className="mx-auto mt-6 max-w-6xl text-xs text-sidebar-foreground/50">
        © {new Date().getFullYear()} CLOUT. All rights reserved.
      </p>
    </footer>
  );
}

function LandingPage() {
  return (
    <div className="flex flex-1 flex-col">
      <Nav />
      <Hero />
      <VisualStories />
      <HowItWorks />
      <Benefits />
      <PaymentsSection />
      <WhyClout />
      <MotivationBanner />
      <Footer />
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const isBootstrapping = useAuthStore((s) => s.isBootstrapping);

  useEffect(() => {
    if (isBootstrapping || !user) return;
    router.replace(`/${user.user_type}/dashboard`);
  }, [isBootstrapping, user, router]);

  if (isBootstrapping || user) {
    return (
      <main className="flex min-h-screen flex-1 items-center justify-center text-sm text-muted-foreground">
        Loading...
      </main>
    );
  }

  return <LandingPage />;
}
