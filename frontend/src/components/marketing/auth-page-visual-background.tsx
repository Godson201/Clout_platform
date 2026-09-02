import Image from "next/image";

export function AuthPageVisualBackground() {
  return (
    <>
      <Image
        src="/images/clout-registration-collaboration-v1.png"
        alt=""
        fill
        priority
        quality={90}
        sizes="100vw"
        className="pointer-events-none object-cover object-[72%_center]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(3,22,38,0.84)_0%,rgba(3,22,38,0.62)_48%,rgba(3,22,38,0.24)_100%)]"
      />
    </>
  );
}
