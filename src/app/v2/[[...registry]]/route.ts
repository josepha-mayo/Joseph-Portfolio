import r24 from '@/generated/von-registry-r24.json';
import r35 from '@/generated/von-registry-r35.json';
import r61 from '@/generated/von-registry-r61.json';
import { registryResponse } from '@/lib/von-registry';
import { resolveParentRedirect, staticMetadataRedirect } from '@/lib/von-registry-parent';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function selected(request: Request) {
  const path = new URL(request.url).pathname;
  if (path.startsWith('/v2/von-rag-r61/')) return { data: r61, assets: 'r61' };
  if (path.startsWith('/v2/von-rag-r35/')) return { data: r35, assets: 'r35' };
  return { data: r24, assets: 'r24' };
}
async function read(request: Request) {
  const choice = selected(request);
  return resolveParentRedirect(request,
    staticMetadataRedirect(request, registryResponse(request, choice.data), choice.assets));
}
function write(request: Request) {
  return registryResponse(request, selected(request).data);
}

export async function GET(request: Request) { return read(request); }
export async function HEAD(request: Request) { return read(request); }
export function POST(request: Request) { return write(request); }
export function PUT(request: Request) { return write(request); }
export function PATCH(request: Request) { return write(request); }
export function DELETE(request: Request) { return write(request); }
