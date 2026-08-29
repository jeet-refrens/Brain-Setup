import { type Mongoose, type InferSchemaType, Schema } from 'mongoose';
import isURL from 'validator/lib/isURL';
import signatureRequestStatus from '@refrens/fence/invoices/signatureRequestStatus.json';
import signerStatus from '@refrens/fence/invoices/signerStatus.json';
import signerRole from '@refrens/fence/invoices/signerRole.json';
import signatureType from '@refrens/fence/invoices/signatureType.json';
import documentTypes from '@refrens/fence/invoices/documentTypes.json';
import { Email } from './helpers/stringTypes';

const SignerSchema = new Schema(
  {
    signerEmail: Email({ required: true }),
    signerName: { type: String, required: true },
    role: {
      type: String,
      enum: Object.keys(signerRole),
      required: true,
    },
    signatureType: {
      type: String,
      enum: Object.keys(signatureType),
      required: true,
    },
    signURL: { type: String, validate: { validator: (v: string) => !v || isURL(v) } },
    status: {
      type: String,
      enum: Object.keys(signerStatus),
      default: signerStatus.REQUESTED,
    },
    signedAt: { type: Date },
  },
  {
    timestamps: false,
    strict: 'throw',
  },
);

const DocumentSignatureRequestsSchema = new Schema(
  {
    business: {
      type: Schema.Types.ObjectId,
      ref: 'businesses',
      required: true,
    },
    invoice: {
      type: Schema.Types.ObjectId,
      ref: 'invoices',
      index: true,
      required: true,
    },
    // ref to the invoice audit version that was active when sign request was created
    invoiceAuditId: {
      type: Schema.Types.ObjectId,
      ref: 'invoiceaudits',
      index: true,
    },
    // extensible for future document types: quotation, client statement, etc.
    documentType: {
      type: String,
      enum: Object.keys(documentTypes),
      default: 'INVOICE',
    },
    status: {
      type: String,
      enum: Object.keys(signatureRequestStatus),
      default: signatureRequestStatus.PENDING,
    },
    // Digio's document ID for API reference; unique+sparse so webhook lookup resolves to exactly one DSR
    vendorDocId: { type: String, index: { unique: true, sparse: true }, maxLength: 100 },
    signers: {
      type: [SignerSchema],
      default: [],
    },
    // S3 key of the signed PDF returned by Digio after signing
    signedPDF: { type: String },
    // Digio sign link expiry: createdAt + expireInDays (currently 10).
    // Used by the expire-digio-sign-requests cron to find stale PENDING requests.
    expiresAt: { type: Date },
    // Last time the DSR was synced from Digio via refresh. Used to enforce 5-min cooldown on frontend.
    lastSyncedAt: { type: Date },
    _systemMeta: { type: Schema.Types.Mixed },
  },
  {
    timestamps: true,
    strict: 'throw',
  },
);

// compound index: expire cron queries status (equality) + expiresAt (range); ESR ordering
DocumentSignatureRequestsSchema.index({ status: 1, expiresAt: 1 });

export type IDocumentSignatureRequest = InferSchemaType<typeof DocumentSignatureRequestsSchema>;

/**
 * @param app - The Feathers application instance
 */
export default function DocumentSignatureRequestsModel(app: any) {
  const mongooseClient: Mongoose = app.get('mongooseClient');

  return mongooseClient.model('documentSignatureRequests', DocumentSignatureRequestsSchema);
}
