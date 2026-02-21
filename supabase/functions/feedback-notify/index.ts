// Supabase Edge Function: Send email notification when user submits feedback
// Triggered by Database Webhook on INSERT to user_feedback table

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY");
const NOTIFICATION_EMAIL = Deno.env.get("FEEDBACK_NOTIFICATION_EMAIL");

interface FeedbackPayload {
  type: "INSERT";
  table: "user_feedback";
  record: {
    id: string;
    rating: "positive" | "negative";
    feedback_text: string | null;
    contact_info: string | null;
    chapter_number: number;
    environment: string | null;
    created_at: string;
    user_id: string | null;
    client_uuid: string | null;
  };
}

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
      },
    });
  }

  try {
    const payload: FeedbackPayload = await req.json();
    const feedback = payload.record;

    // Format the email
    const isPositive = feedback.rating === "positive";
    const emoji = isPositive ? "👍" : "👎";
    const userType = feedback.user_id ? "Authenticated User" : "Guest User";

    const subject = `${emoji} New ${feedback.rating} feedback on Learning Odyssey`;

    const htmlBody = `
      <h2>${emoji} New Feedback Received</h2>
      <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
          <td style="padding: 8px; font-weight: bold;">Rating:</td>
          <td style="padding: 8px;">${feedback.rating}</td>
        </tr>
        <tr>
          <td style="padding: 8px; font-weight: bold;">User Type:</td>
          <td style="padding: 8px;">${userType}</td>
        </tr>
        <tr>
          <td style="padding: 8px; font-weight: bold;">Chapter:</td>
          <td style="padding: 8px;">${feedback.chapter_number}</td>
        </tr>
        <tr>
          <td style="padding: 8px; font-weight: bold;">Environment:</td>
          <td style="padding: 8px;">${feedback.environment || "N/A"}</td>
        </tr>
        ${feedback.feedback_text ? `
        <tr>
          <td style="padding: 8px; font-weight: bold; vertical-align: top;">Feedback:</td>
          <td style="padding: 8px;">${feedback.feedback_text}</td>
        </tr>
        ` : ""}
        ${feedback.contact_info ? `
        <tr>
          <td style="padding: 8px; font-weight: bold;">Contact:</td>
          <td style="padding: 8px;">${feedback.contact_info}</td>
        </tr>
        ` : ""}
        <tr>
          <td style="padding: 8px; font-weight: bold;">Time:</td>
          <td style="padding: 8px;">${new Date(feedback.created_at).toLocaleString()}</td>
        </tr>
      </table>
    `;

    // Send email via Resend
    const resendResponse = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${RESEND_API_KEY}`,
      },
      body: JSON.stringify({
        from: "Learning Odyssey <feedback@resend.dev>",
        to: [NOTIFICATION_EMAIL],
        subject: subject,
        html: htmlBody,
      }),
    });

    if (!resendResponse.ok) {
      const error = await resendResponse.text();
      throw new Error(`Resend API error: ${error}`);
    }

    const result = await resendResponse.json();
    console.log("Email sent successfully:", result);

    return new Response(JSON.stringify({ success: true, emailId: result.id }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Error sending feedback notification:", error);
    return new Response(
      JSON.stringify({ success: false, error: error.message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
