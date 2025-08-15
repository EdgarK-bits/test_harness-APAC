#include "bits/stdc++.h"
using namespace std; // use std namespace for brevity
template<typename T>
inline void read(T &x){ /// \brief Fast read for signed integers into \p x.
	x=0;char c=getchar();bool f=false; // init accumulator, read first char, sign flag
	for(;!isdigit(c);c=getchar())f!=c=='-'; // scan to first digit; track '-' (as in original logic)
	for(;isdigit(c);c=getchar())x=x*10+c-'0'; // accumulate digits
	if(f)x=-x; // apply sign if flagged
}
template<typename T ,typename ...Arg>
inline void read(T &x,Arg &...args){ /// \brief Variadic fast-read. Reads \p x then remaining \p args.
	read(x);read(args...); // unfold recursion
}
template<typename T>
inline void write(T x){ /// \brief Fast write for signed integers.
	if(x<0)putchar('-'),x=-x; // handle negative
	if(x>=10)write(x/10); // print higher digits
	putchar(x%10+'0'); // print last digit
}
const int kMod=1e9+7; /// \brief Modulo used for all sums.
const int kMaxN=1e6+10; /// \brief Maximum coordinate bound.
struct SegmentTree{
	struct Node{
		int l,r;   ///< \brief Segment [l,r].
		int tag;   ///< \brief Lazy tag meaning "set-to-zero".
		int sum;   ///< \brief Sum on the segment modulo kMod.
	}tree[kMaxN*4]; // static storage for segment tree
	#define lson x<<1 // left child index
	#define rson x<<1|1 // right child index
	void buildTree(int x,int l,int r){ /// \brief Build tree over range [l,r].
		tree[x].l=l,tree[x].r=r; // set node interval
		if(l==r)return; // leaf
		int mid=(l+r)>>1; // midpoint
		buildTree(lson,l,mid); // build left
		buildTree(rson,mid+1,r); // build right
	}
	void pushUp(int x){ /// \brief Pull sums from children.
		tree[x].sum=(tree[lson].sum+tree[rson].sum)%kMod; // parent sum = sum of children
	}
	void pushDown(int x){ /// \brief Propagate "zero" lazy tag to children.
		if(tree[x].tag){
			tree[lson].tag=tree[rson].tag=1; // mark children as zeroed
			tree[lson].sum=tree[rson].sum=0; // clear children sums
			tree[x].tag=0; // clear current tag
		}
	}
	void updatePoint(int x,int pos,int val){ /// \brief Point update: set position \p pos to \p val.
		if(tree[x].l==tree[x].r){
			tree[x].sum=val; // write leaf
			return;
		}
		pushDown(x); // ensure correctness before descending
		int mid=(tree[x].l+tree[x].r)>>1; // midpoint
		if(pos<=mid)updatePoint(lson,pos,val); // go left if needed
		if( mid<pos)updatePoint(rson,pos,val); // go right if needed
		pushUp(x);  // recompute sum
	}
	void zeroRange(int x,int l,int r){ /// \brief Range-assign zero on [l,r] via lazy tag.
		if(l<=tree[x].l&&tree[x].r<=r){
			tree[x].tag=1;tree[x].sum=0; // set lazy zero and clear sum
			return;
		}
		pushDown(x); // push pending tags before splitting
		int mid=(tree[x].l+tree[x].r)>>1; // midpoint
		if(l<=mid)zeroRange(lson,l,r); // zero left overlap
		if(mid<r)zeroRange(rson,l,r); // zero right overlap
		pushUp(x); // recompute sum
	}
	int queryRange(int x,int l,int r){ /// \brief Query sum on [l,r] modulo kMod.
		if(l<=tree[x].l&&tree[x].r<=r)return tree[x].sum; // fully covered
		pushDown(x); // ensure children are up-to-date
		int tmp=0,mid=(tree[x].l+tree[x].r)>>1; // accumulator and midpoint
		if(l<=mid)(tmp+=queryRange(lson,l,r))%=kMod; // collect left
		if(mid<r)(tmp+=queryRange(rson,l,r))%=kMod; // collect right
		return tmp; // return combined sum
	}
}seg; // global segment tree instance
int nRows,mCols,qCount; // grid dimensions and number of rectangles
vector<pair<int,int>>addRanges[1000010],delRanges[1000010]; // intervals added/removed per row
set<pair<int,int>>activeSegs; // active intervals set, ordered by (l,r)
signed main(){
	read(nRows,mCols,qCount); // read problem sizes
	while(qCount--){
		int x1,y1,x2,y2; // rectangle corners
		read(x1,y1,x2,y2); // read rectangle
		addRanges[x1].push_back(make_pair(y1,y2)); // add at start row
		delRanges[x2+1].push_back(make_pair(y1,y2)); // schedule removal after end row
	}
	activeSegs.insert({0,0}); // sentinel interval
	for(auto segRange:addRanges[1])
		activeSegs.insert(segRange); // preload row 1 intervals
	seg.buildTree(1,1,mCols); // build DP segment tree over columns
	seg.updatePoint(1,1,1); // base case: 1 way at column 1
	for(int i=2;i<=nRows;i++){
		sort(addRanges[i].begin(),addRanges[i].end()); // sort by (l,r)
		reverse(addRanges[i].begin(),addRanges[i].end()); // process from larger l if needed
		for(auto segRange:addRanges[i]){
			int x=segRange.first,y=segRange.second; // current interval [x,y]
			if (y==mCols) continue; // cannot extend beyond last column
			auto it=activeSegs.lower_bound(make_pair(y+2,0));it--; // predecessor with l<=y+1
			int ans=0; // DP sum for column y+1
			auto pr=*it; // best predecessor interval
			if(pr.second<=y)ans=seg.queryRange(1,pr.second+1,y+1); // sum ways over allowed range
			seg.updatePoint(1,y+1,ans); // write DP at y+1
		}
		for(auto segRange:delRanges[i])
			activeSegs.erase(segRange); // remove intervals ending before row i
		for(auto segRange:addRanges[i])
			activeSegs.insert(segRange), // activate new intervals
			seg.zeroRange(1,segRange.first,segRange.second); // invalidate DP in blocked range
	}
	auto it=activeSegs.end();it--; // last (max) interval
	printf("%d",seg.queryRange(1,(*it).second+1,mCols)); // answer: sum over allowed tail range
}
