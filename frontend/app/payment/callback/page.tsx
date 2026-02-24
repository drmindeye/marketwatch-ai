import { redirect } from "next/navigation";
import Link from "next/link";

interface Props {
  searchParams: Promise<{ reference?: string; trxref?: string }>;
}

export default async function PaymentCallbackPage({ searchParams }: Props) {
  const params = await searchParams;
  const reference = params.reference ?? params.trxref;

  if (!reference) {
    redirect("/dashboard");
  }

  // Verify transaction server-side via Paystack
  const res = await fetch(
    `https://api.paystack.co/transaction/verify/${reference}`,
    {
      headers: {
        Authorization: `Bearer ${process.env.PAYSTACK_SECRET_KEY}`,
      },
      cache: "no-store",
    }
  );

  const json = await res.json() as {
    status: boolean;
    data?: { status: string; metadata?: { plan: string } };
  };

  const success =
    json.status && json.data?.status === "success";

  return (
    <div className="flex min-h-screen items-center justify-center bg-black px-4 text-center">
      <div className="max-w-sm">
        {success ? (
          <>
            <div className="mb-4 text-5xl">🎉</div>
            <h1 className="text-2xl font-bold text-white">Payment Successful!</h1>
            <p className="mt-3 text-white/50">
              Your account has been upgraded. It may take a few seconds to reflect.
            </p>
          </>
        ) : (
          <>
            <div className="mb-4 text-5xl">❌</div>
            <h1 className="text-2xl font-bold text-white">Payment Failed</h1>
            <p className="mt-3 text-white/50">
              Something went wrong. Please try again or contact support.
            </p>
          </>
        )}

        <Link
          href="/dashboard"
          className="mt-8 inline-block rounded-lg bg-emerald-500 px-6 py-3 text-sm font-semibold text-black hover:bg-emerald-400"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
