import Header from "@/components/layout/Header";
import Hero from "@/components/landing/Hero";
import Features from "@/components/landing/Features";
import Pricing from "@/components/landing/Pricing";
import FAQ from "@/components/landing/FAQ";
import Footer from "@/components/layout/Footer";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <Header />
      <Hero />
      <Features />
      <Pricing />
      <FAQ />
      <Footer />
    </main>
  );
}
