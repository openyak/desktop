import Image from "next/image";

interface OpenYakLogoProps {
  size?: number;
  className?: string;
}

export function OpenYakLogo({ size = 20, className }: OpenYakLogoProps) {
  return (
    <Image
      src="/favicon.svg"
      width={size}
      height={size}
      alt="OpenYak"
      className={className}
      unoptimized
    />
  );
}
